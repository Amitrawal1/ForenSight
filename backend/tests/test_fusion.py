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


def test_face_swap_not_cancelled_by_ai_model_saying_real():
    face = DetectorResult(name="face_swap", fake_score=0.98, reliability=0.5, fake_kind="manipulated")
    ai_model = DetectorResult(name="ai_image", fake_score=0.0, reliability=0.7, fake_kind="ai_generated")
    assert combine([face, ai_model])[0] == "manipulated"


def test_one_weak_check_alone_cannot_decide():
    weak = DetectorResult(name="ela", fake_score=0.7, reliability=0.35, fake_kind="manipulated")
    assert combine([weak])[0] == "inconclusive"


def test_weak_nothing_found_does_not_block_authentic():
    ai_model = DetectorResult(name="ai_image", fake_score=0.0, reliability=0.7, fake_kind="ai_generated")
    ela_nothing = DetectorResult(name="ela", fake_score=0.2, reliability=0.15, fake_kind="manipulated")
    assert combine([ai_model, ela_nothing])[0] == "likely_authentic"
