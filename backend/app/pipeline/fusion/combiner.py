"""Combine independent detector results into one verdict.

1. If a check found proof (decisive=True, e.g. "made by AI" written in the file), use it.
2. Otherwise take an average of all fake scores, where checks we trust more count more.
3. Instead of forcing a guess, a middle score (or too little evidence) gives "inconclusive".
"""

from app.pipeline.detectors.base import DetectorResult

AUTHENTIC_BELOW = 0.35
FAKE_ABOVE = 0.65
MIN_TOTAL_RELIABILITY = 0.5


def combine(results: list[DetectorResult]) -> tuple[str, float]:
    """Return (verdict, confidence 0..1). Inconclusive always has confidence 0."""
    # Proof-like findings (e.g. the AI tool labelled the file itself) decide on their own
    decisive = [r for r in results if r.decisive and r.fake_score > FAKE_ABOVE]
    if decisive:
        best = max(decisive, key=lambda r: r.fake_score)
        return best.fake_kind, best.fake_score

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
