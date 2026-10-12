"""Contract every detector follows.

Each detector is independent and looks for one kind of clue. It returns a score plus
human-readable reasons and optional localisation (heatmap / time segments), so the
final explanation is simply the list of detectors that fired.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Segment:
    start_s: float
    end_s: float
    score: float


@dataclass
class DetectorResult:
    name: str
    # 0.0 = looks real, 1.0 = looks fake
    fake_score: float
    # How much this detector trusts its own score (0..1); low for e.g. tiny/compressed inputs
    reliability: float
    # "ai_generated" | "manipulated" — what kind of fake this detector points to
    fake_kind: str = "manipulated"
    reasons: list[str] = field(default_factory=list)
    heatmap_path: Path | None = None
    segments: list[Segment] = field(default_factory=list)


class Detector(ABC):
    name: str
    media_types: tuple[str, ...]

    @abstractmethod
    def run(self, path: Path) -> DetectorResult: ...
