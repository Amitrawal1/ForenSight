"""Turn detector results into a plain-language summary and the top reasons.

Templates only: every sentence comes from a detector's own findings, nothing is invented.
"""

from app.pipeline.detectors.base import DetectorResult

SUMMARY = {
    "likely_authentic": "No significant signs of AI generation or manipulation were found.",
    "ai_generated": "This content appears to have been created by an AI model.",
    "manipulated": "This content appears to be real but partly changed or edited.",
    "inconclusive": "The evidence is weak or mixed, so ForenSight does not make a call.",
}

TOP_N = 3


def explain(verdict: str, results: list[DetectorResult]) -> tuple[str, list[str]]:
    """Return (summary sentence, top reasons supporting the verdict)."""
    if verdict in ("ai_generated", "manipulated"):
        # Explain with the checks that found this kind of fake
        relevant = [r for r in results if r.fake_score > 0.5 and r.fake_kind == verdict]
    elif verdict == "likely_authentic":
        relevant = [r for r in results if r.fake_score < 0.5]
    else:
        relevant = list(results)

    # Strongest evidence first: reliable detectors that are far from 0.5
    relevant.sort(key=lambda r: r.reliability * abs(r.fake_score - 0.5), reverse=True)
    reasons = [r.reasons[0] for r in relevant if r.reasons and r.reliability > 0][:TOP_N]
    return SUMMARY[verdict], reasons
