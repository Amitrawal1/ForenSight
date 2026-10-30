from app.pipeline.detectors.base import DetectorResult
from app.pipeline.explain.reasons import explain


def r(score, rel, reasons):
    return DetectorResult(name="t", fake_score=score, reliability=rel, reasons=reasons)


def test_inconclusive_shows_why_a_check_counts_little():
    _, reasons = explain("inconclusive", [r(1.0, 0.12, ["Sounds like AI.", "The recording is compressed."])])
    assert reasons == ["Sounds like AI.", "The recording is compressed."]


def test_fake_verdict_shows_only_the_main_reason_of_each_check():
    _, reasons = explain("manipulated", [r(0.9, 0.5, ["Face swapped.", "Extra detail."])])
    assert reasons == ["Face swapped."]
