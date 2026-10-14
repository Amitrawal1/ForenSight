"""Run the full pipeline on one file: detectors -> fusion -> explanation."""

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.pipeline.detectors.base import Detector, DetectorResult, MediaContext
from app.pipeline.detectors.image.ai_image import AiImageDetector
from app.pipeline.detectors.image.ela import ElaDetector
from app.pipeline.detectors.image.face_swap import FaceSwapDetector
from app.pipeline.detectors.image.fft import FftDetector
from app.pipeline.detectors.metadata.detector import MetadataDetector
from app.pipeline.explain.reasons import explain
from app.pipeline.fusion.combiner import combine
from app.pipeline.models.registry import ModelNotAvailable
from app.pipeline.preprocessing.audio import SAMPLE_RATE, AudioDecodeError, load_audio, waveform_peaks
from app.pipeline.preprocessing.thumbnail import make_image_thumbnail

log = logging.getLogger(__name__)

DETECTORS: list[Detector] = [
    MetadataDetector(),
    AiImageDetector(),
    FaceSwapDetector(),
    ElaDetector(),
    FftDetector(),
]

NOT_YET_SUPPORTED = {
    "video": "Video analysis is not available yet (planned for Phase 4).",
    "audio": "Audio analysis is not available yet (planned for Phase 3).",
}


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

    if media_type == "audio":
        try:
            ctx.audio = load_audio(path)
            media = {"duration_s": round(len(ctx.audio) / SAMPLE_RATE, 2), "peaks": waveform_peaks(ctx.audio)}
        except AudioDecodeError as e:
            notes.append(f"The audio could not be analysed: {e}.")
            media_type = "unreadable"  # no detector will run

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

    if media_type in NOT_YET_SUPPORTED:
        notes.append(NOT_YET_SUPPORTED[media_type])

    detector_results = [r for _, r in results]
    verdict, confidence = combine(detector_results)
    summary, reasons = explain(verdict, detector_results)

    thumbnail = make_image_thumbnail(path, out_dir) if media_type == "image" else None

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
