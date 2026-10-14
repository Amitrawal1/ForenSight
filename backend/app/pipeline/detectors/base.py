"""Contract every detector follows.

Each detector is independent and looks for one kind of clue. It returns a score plus
human-readable reasons and optional localisation (heatmap / time segments), so the
final explanation is simply the list of detectors that fired.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Segment:
    start_s: float
    end_s: float
    score: float


@dataclass
class MediaContext:
    path: Path
    media_type: str  # image | video | audio
    mime: str
    # Where the detector may write heatmaps / spectra (storage/artifacts/<analysis id>/)
    out_dir: Path
    # Decoded sound (16 kHz mono float32), filled in by the runner for audio files.
    # Decoding once here means every audio check can reuse it.
    audio: np.ndarray | None = None


@dataclass
class DetectorResult:
    name: str
    # 0.0 = looks real, 1.0 = looks fake
    fake_score: float
    # How much this detector trusts its own score (0..1); low for e.g. tiny/compressed inputs.
    # 0 means "informational only" — shown to the user but ignored by fusion.
    reliability: float
    # "ai_generated" | "manipulated" — what kind of fake this detector points to
    fake_kind: str = "manipulated"
    reasons: list[str] = field(default_factory=list)
    # True for proof-like findings, e.g. the AI tool wrote "made by AI" into the file.
    # A decisive fake finding decides the verdict on its own (see fusion/combiner.py).
    decisive: bool = False
    # File name inside MediaContext.out_dir
    heatmap: str | None = None
    segments: list[Segment] = field(default_factory=list)


class Detector(ABC):
    name: str
    label: str  # shown in the UI
    media_types: tuple[str, ...]

    @abstractmethod
    def run(self, ctx: MediaContext) -> DetectorResult | None:
        """Return None when the check does not apply to this file (e.g. ELA on a PNG)."""
