"""Combine independent detector results into one verdict.

1. If a check found proof (decisive=True, e.g. "made by AI" written in the file), use it.
2. Otherwise score each kind of fake separately:
     - "ai_generated": the whole image was made by AI
     - "manipulated":  a real image where something was changed (face swap, edit)
   Why separately? "Not made by AI" is no evidence against "face was swapped",
   so these checks must not cancel each other out.
3. Each kind's score is an average where checks we trust more count more. We also add
   a neutral 50% "starting guess", so one weak check alone can't decide the verdict.
4. "Likely authentic" needs enough evidence, clean scores, and no check strongly
   suspecting a fake.
5. Instead of forcing a guess, unclear scores (or too little evidence) give "inconclusive".
"""

from app.pipeline.detectors.base import DetectorResult

AUTHENTIC_BELOW = 0.35
FAKE_ABOVE = 0.65
MIN_TOTAL_RELIABILITY = 0.5
# Weight of the neutral 50% starting guess in each kind's average
PRIOR_WEIGHT = 0.3
# A kind only counts as "checked" if the checks looking at it have at least this much
# trust together. E.g. ELA saying "found nothing" (trust 0.15) alone is too weak.
CHECKED_MIN_TRUST = 0.3
# A check this sure that the file is fake blocks "likely authentic", even if we trust
# it too little to call the file fake. (Example: the AI-voice model is 100% sure, but the
# audio is compressed, so it counts little. That is no reason to say "authentic".)
STRONG_FAKE = 0.9
KINDS = ("ai_generated", "manipulated")


def kind_score(results: list[DetectorResult], kind: str) -> tuple[float, float]:
    """Return (fake score 0..1, total trust) for one kind of fake."""
    same = [r for r in results if r.fake_kind == kind and r.reliability > 0]
    trust = sum(r.reliability for r in same)
    score = (sum(r.fake_score * r.reliability for r in same) + 0.5 * PRIOR_WEIGHT) / (trust + PRIOR_WEIGHT)
    return score, trust


def combine(results: list[DetectorResult]) -> tuple[str, float]:
    """Return (verdict, confidence 0..1). Inconclusive always has confidence 0."""
    # Proof-like findings (e.g. the AI tool labelled the file itself) decide on their own
    decisive = [r for r in results if r.decisive and r.fake_score > FAKE_ABOVE]
    if decisive:
        best = max(decisive, key=lambda r: r.fake_score)
        return best.fake_kind, best.fake_score

    scores = {kind: kind_score(results, kind) for kind in KINDS}

    # Fake: the strongest kind above the line wins
    kind, (score, _) = max(scores.items(), key=lambda item: item[1][0])
    if score > FAKE_ABOVE:
        return kind, score

    # Authentic: enough evidence overall, and every kind that was properly checked looks clean
    checked = [s for s, trust in scores.values() if trust >= CHECKED_MIN_TRUST]
    total_trust = sum(trust for _, trust in scores.values())
    strong_doubt = any(r.reliability > 0 and r.fake_score >= STRONG_FAKE for r in results)
    if checked and total_trust >= MIN_TOTAL_RELIABILITY and max(checked) < AUTHENTIC_BELOW and not strong_doubt:
        return "likely_authentic", 1 - max(checked)

    return "inconclusive", 0.0
