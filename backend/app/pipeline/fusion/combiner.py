"""Combine independent detector results into one verdict.

Reliability-weighted average of fake scores. Instead of forcing a guess, a middle
band (or too little reliable evidence) yields "inconclusive".
"""

from app.pipeline.detectors.base import DetectorResult

AUTHENTIC_BELOW = 0.35
FAKE_ABOVE = 0.65
MIN_TOTAL_RELIABILITY = 0.5


def combine(results: list[DetectorResult]) -> tuple[str, float]:
    """Return (verdict, confidence 0..1). Inconclusive always has confidence 0."""
    total = sum(r.reliability for r in results)
    if total < MIN_TOTAL_RELIABILITY:
        return "inconclusive", 0.0

    score = sum(r.fake_score * r.reliability for r in results) / total

    if score < AUTHENTIC_BELOW:
        return "likely_authentic", 1 - score
    if score > FAKE_ABOVE:
        fired = [r for r in results if r.fake_score > FAKE_ABOVE]
        ai_weight = sum(r.reliability for r in fired if r.fake_kind == "ai_generated")
        manip_weight = sum(r.reliability for r in fired if r.fake_kind == "manipulated")
        verdict = "ai_generated" if ai_weight > manip_weight else "manipulated"
        return verdict, score
    return "inconclusive", 0.0
