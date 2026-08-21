from aurora.research.hypotheses import ResearchHypothesis


def test_hypothesis_basic():
    hyp = ResearchHypothesis(
        hypothesis_id="hyp_001",
        source_claim_id="claim_001",
        document_id="doc_001",
        methodology="gann",
        condition="price above 200 SMA",
        expected_effect="bullish continuation",
        target_variable="price",
        horizon="swing",
        direction="long",
    )
    assert hyp.test_status == "untested"
    assert hyp.direction == "long"
    assert hyp.horizon == "swing"


def test_hypothesis_all_statuses():
    for status in ["untested", "supported", "weak", "rejected", "conflicting"]:
        hyp = ResearchHypothesis(
            hypothesis_id=f"hyp_{status}",
            source_claim_id="claim_001",
            document_id="doc_001",
            methodology="unknown",
            test_status=status,  # type: ignore[arg-type]
        )
        assert hyp.test_status == status


def test_hypothesis_default_untested():
    hyp = ResearchHypothesis(
        hypothesis_id="hyp_001",
        source_claim_id="claim_001",
        document_id="doc_001",
        methodology="unknown",
    )
    assert hyp.test_status == "untested"


def test_hypothesis_serialization_round_trip():
    hyp = ResearchHypothesis(
        hypothesis_id="hyp_001",
        source_claim_id="claim_001",
        document_id="doc_001",
        methodology="fibonacci",
        condition="retracement at 61.8%",
        expected_effect="bounce",
    )
    data = hyp.model_dump()
    restored = ResearchHypothesis.model_validate(data)
    assert restored.hypothesis_id == hyp.hypothesis_id
    assert restored.methodology == "fibonacci"
