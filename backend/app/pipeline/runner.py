"""Run the full pipeline on one file: detectors -> fusion -> explanation."""

import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image

from app.pipeline.detectors.audio.splice import SpliceDetector
from app.pipeline.detectors.audio.voice_clone import VoiceCloneDetector
from app.pipeline.detectors.base import Detector, DetectorResult, MediaContext
from app.pipeline.detectors.image.ai_image import AiImageDetector
from app.pipeline.detectors.image.ela import ElaDetector
from app.pipeline.detectors.image.face_swap import FaceSwapDetector
from app.pipeline.detectors.image.fft import FftDetector
from app.pipeline.detectors.metadata.detector import MetadataDetector
from app.pipeline.detectors.video.ai_frames import VideoAiFramesDetector
from app.pipeline.detectors.video.faces import VideoFaceSwapDetector
from app.pipeline.explain.reasons import explain
from app.pipeline.fusion.combiner import combine
from app.pipeline.models.registry import ModelNotAvailable
from app.pipeline.preprocessing.audio import SAMPLE_RATE, AudioDecodeError, load_audio, waveform_peaks
from app.pipeline.preprocessing.spectrogram import SPECTROGRAM_NAME, save_spectrogram
from app.pipeline.preprocessing.thumbnail import THUMB_NAME, image_size, make_image_thumbnail
from app.pipeline.preprocessing.video import VideoDecodeError, sample_frames, save_frame_previews

log = logging.getLogger(__name__)

DETECTORS: list[Detector] = [
    MetadataDetector(),
    AiImageDetector(),
    FaceSwapDetector(),
    ElaDetector(),
    FftDetector(),
    VideoFaceSwapDetector(),
    VideoAiFramesDetector(),
    VoiceCloneDetector(),
    SpliceDetector(),
]

# Overall progress: reading the file ends at READ_END, then the checks share the
# percentages up to CHECKS_END. The last part is for writing the verdict.
READ_END = 15
CHECKS_END = 95
# Rough share of the work per check. Only used for the progress bar, never for scores.
CHECK_COST = {
    "metadata": 1,
    "ai_image": 6,
    "face_swap": 10,
    "ela": 1,
    "fft": 1,
    "video_face_swap": 40,
    "video_ai_frames": 25,
    "voice_clone": 25,
    "audio_splice": 2,
}
AUDIO_CHECKS = ("voice_clone", "audio_splice")
CHECK_STEP = {
    "metadata": "Checking metadata",
    "ai_image": "Checking the image for AI",
    "face_swap": "Checking faces",
    "ela": "Checking for edits",
    "fft": "Checking image patterns",
    "video_face_swap": "Checking faces",
    "video_ai_frames": "Checking frames for AI",
    "voice_clone": "Listening for AI voice",
    "audio_splice": "Checking for audio joins",
}


class ProgressTracker:
    """Pass progress to the callback. It never moves backward and its errors are ignored."""

    def __init__(self, callback: Callable[[int, str], None] | None):
        self.callback = callback
        self.percent = 0

    def __call__(self, percent: float, step: str) -> None:
        self.percent = max(self.percent, min(100, int(percent)))
        if self.callback is None:
            return
        try:
            self.callback(self.percent, step)
        except Exception:
            log.exception("progress callback failed")


def run_checks(checks: list[Detector], ctx: MediaContext, progress: ProgressTracker,
               notes: list[str]) -> list[tuple[Detector, DetectorResult]]:
    """Run each check and give each one a share of the progress bar that fits its cost."""
    # Without sound the audio checks stop at once, so they get no share
    costs = [0 if ctx.audio is None and det.name in AUDIO_CHECKS else CHECK_COST.get(det.name, 1) for det in checks]
    per_cost = (CHECKS_END - READ_END) / max(sum(costs), 1)
    start = float(READ_END)

    results: list[tuple[Detector, DetectorResult]] = []
    for det, cost in zip(checks, costs):
        progress(start, CHECK_STEP.get(det.name, det.label))
        share = cost * per_cost
        ctx.on_item = lambda done, total, step, start=start, share=share: progress(start + share * done / total, step)
        start += share
        try:
            res = det.run(ctx)
        except ModelNotAvailable as e:
            # Model not installed yet: skip this check and tell the user why
            log.warning("detector %s skipped: %s", det.name, e)
            notes.append(f"The {det.label.lower()} check was skipped: {e}")
            continue
        except Exception:
            # One broken check must not sink the whole analysis
            log.exception("detector %s failed", det.name)
            notes.append(f"The {det.label.lower()} check could not run on this file.")
            continue
        if res is not None:
            results.append((det, res))
    return results


def add_frame_previews(media: dict, frames: list, out_dir: Path) -> None:
    """Extra evidence for the result page. A failure only leaves it out."""
    try:
        media["height"], media["width"] = frames[0].rgb.shape[:2]
        media["frames"] = save_frame_previews(frames, out_dir)
    except Exception:
        log.exception("could not save frame previews")


def add_spectrogram(media: dict, audio, out_dir: Path) -> None:
    """Extra evidence for the result page. A failure only leaves it out."""
    try:
        save_spectrogram(audio, out_dir / SPECTROGRAM_NAME)
        media["spectrogram"] = SPECTROGRAM_NAME
    except Exception:
        log.exception("could not draw the spectrogram")


def add_image_size(media: dict, path: Path) -> None:
    """Extra evidence for the result page. A failure only leaves it out."""
    try:
        media["width"], media["height"] = image_size(path)
    except Exception:
        log.exception("could not read the image size")


@dataclass
class Outcome:
    verdict: str
    confidence: float
    summary: str
    reasons: list[str]
    detectors: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    thumbnail: str | None = None
    # Extra info for the result page, e.g. audio duration and waveform
    media: dict = field(default_factory=dict)

    def evidence(self) -> dict:
        return {
            "summary": self.summary,
            "reasons": self.reasons,
            "detectors": self.detectors,
            "notes": self.notes,
            "media": self.media,
        }


def analyse(path: Path, media_type: str, mime: str, out_dir: Path,
            on_progress: Callable[[int, str], None] | None = None) -> Outcome:
    """Check one file. `on_progress(percent, step)` is called along the way, if given."""
    progress = ProgressTracker(on_progress)
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = MediaContext(path=path, media_type=media_type, mime=mime, out_dir=out_dir)

    notes: list[str] = []
    media: dict = {}

    if media_type == "image":
        progress(0, "Reading the image")
        add_image_size(media, path)

    if media_type == "video":
        progress(0, "Reading video frames")
        try:
            ctx.frames, duration = sample_frames(path, out_dir / "frames")
            media["duration_s"] = round(duration, 2)
            # Thumbnail = the middle frame
            Image.fromarray(ctx.frames[len(ctx.frames) // 2].rgb).save(out_dir / THUMB_NAME, quality=85)
            add_frame_previews(media, ctx.frames, out_dir)
        except VideoDecodeError as e:
            notes.append(f"The video could not be analysed: {e}.")
            media_type = "unreadable"

    if media_type in ("audio", "video"):
        progress(8 if media_type == "video" else 0, "Reading the sound")
        try:
            ctx.audio = load_audio(path)
            media["peaks"] = waveform_peaks(ctx.audio)
            media.setdefault("duration_s", round(len(ctx.audio) / SAMPLE_RATE, 2))
            progress(13, "Drawing the spectrogram")
            add_spectrogram(media, ctx.audio, out_dir)
        except AudioDecodeError as e:
            if media_type == "audio":
                notes.append(f"The audio could not be analysed: {e}.")
                media_type = "unreadable"  # no detector will run
            else:
                notes.append("The video has no readable sound track, so only the picture was checked.")

    checks = [det for det in DETECTORS if media_type in det.media_types]
    results = run_checks(checks, ctx, progress, notes)

    progress(CHECKS_END, "Writing the verdict")
    detector_results = [r for _, r in results]
    verdict, confidence = combine(detector_results)
    summary, reasons = explain(verdict, detector_results)

    if media_type == "image":
        thumbnail = make_image_thumbnail(path, out_dir)
    else:
        thumbnail = THUMB_NAME if (out_dir / THUMB_NAME).is_file() else None

    return Outcome(
        verdict=verdict,
        confidence=round(confidence, 3),
        summary=summary,
        reasons=reasons,
        detectors=[{"label": det.label, **asdict(res)} for det, res in results],
        notes=notes,
        thumbnail=thumbnail,
        media=media,
    )
