"""Run the full pipeline on one file: detectors -> fusion -> explanation."""

import logging
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
from app.pipeline.preprocessing.thumbnail import THUMB_NAME, make_image_thumbnail
from app.pipeline.preprocessing.video import VideoDecodeError, sample_frames

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


def analyse(path: Path, media_type: str, mime: str, out_dir: Path) -> Outcome:
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = MediaContext(path=path, media_type=media_type, mime=mime, out_dir=out_dir)

    results: list[tuple[Detector, DetectorResult]] = []
    notes: list[str] = []
    media: dict = {}

    if media_type == "video":
        try:
            ctx.frames, duration = sample_frames(path, out_dir / "frames")
            media["duration_s"] = round(duration, 2)
            # Thumbnail = the middle frame
            Image.fromarray(ctx.frames[len(ctx.frames) // 2].rgb).save(out_dir / THUMB_NAME, quality=85)
        except VideoDecodeError as e:
            notes.append(f"The video could not be analysed: {e}.")
            media_type = "unreadable"

    if media_type in ("audio", "video"):
        try:
            ctx.audio = load_audio(path)
            media["peaks"] = waveform_peaks(ctx.audio)
            media.setdefault("duration_s", round(len(ctx.audio) / SAMPLE_RATE, 2))
        except AudioDecodeError as e:
            if media_type == "audio":
                notes.append(f"The audio could not be analysed: {e}.")
                media_type = "unreadable"  # no detector will run
            else:
                notes.append("The video has no readable sound track, so only the picture was checked.")

    for det in DETECTORS:
        if media_type not in det.media_types:
            continue
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
