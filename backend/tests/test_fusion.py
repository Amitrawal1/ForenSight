from app.pipeline.detectors.base import DetectorResult
from app.pipeline.fusion.combiner import combine


def r(score, rel=1.0, kind="manipulated"):
    return DetectorResult(name="t", fake_score=score, reliability=rel, fake_kind=kind)


def test_authentic():
    assert combine([r(0.1), r(0.2)])[0] == "likely_authentic"


def test_ai_generated():
    assert combine([r(0.9, kind="ai_generated"), r(0.8, kind="ai_generated")])[0] == "ai_generated"


def test_mixed_is_inconclusive():
    assert combine([r(0.1), r(0.9)])[0] == "inconclusive"


def test_no_reliable_evidence_is_inconclusive():
    assert combine([r(0.9, rel=0.1)]) == ("inconclusive", 0.0)


def test_decisive_finding_wins_over_disagreement():
    proof = DetectorResult(name="meta", fake_score=0.95, reliability=0.9, fake_kind="ai_generated", decisive=True)
    assert combine([proof, r(0.0, rel=0.7)])[0] == "ai_generated"
