from __future__ import annotations

from dataclasses import dataclass

from aurora.hypothesis.engine import HypothesisEngine, TestableHypothesis
from aurora.hypothesis.provenance import FeatureProvenanceRegistry, ProvenanceRecord
from aurora.research.claims import ResearchClaim
from aurora.research.hypotheses import ResearchHypothesis


@dataclass(frozen=True)
class ClaimFeatureBridge:
    hypothesis_engine: HypothesisEngine
    provenance_registry: FeatureProvenanceRegistry

    def claim_to_hypothesis(
        self,
        claim: ResearchClaim,
        hypothesis_id: str,
        feature_requirements: list[str] | None = None,
    ) -> TestableHypothesis:
        hypothesis = TestableHypothesis(
            hypothesis_id=hypothesis_id,
            source_claim_ids=[claim.claim_id],
            methodology=claim.methodology if claim.methodology else "unknown",
            condition=claim.normalized_text[:500] if claim.normalized_text else "",
            feature_requirements=feature_requirements or [],
            target="",
            horizon="unknown",
            direction="unknown",
            assumptions=[],
            implementation_status="not_implemented",
            validation_status="untested",
            notes=f"Derived from claim {claim.claim_id}",
        )
        self.hypothesis_engine.register(hypothesis)
        return hypothesis

    def research_hypothesis_to_testable(
        self,
        research_hyp: ResearchHypothesis,
    ) -> TestableHypothesis:
        hypothesis = TestableHypothesis(
            hypothesis_id=research_hyp.hypothesis_id,
            source_claim_ids=[research_hyp.source_claim_id],
            methodology=research_hyp.methodology,
            condition=research_hyp.condition,
            feature_requirements=[],
            target=research_hyp.target_variable,
            horizon=research_hyp.horizon,
            direction=research_hyp.direction,
            assumptions=[],
            implementation_status="not_implemented",
            validation_status="untested",
            notes=research_hyp.notes,
        )
        self.hypothesis_engine.register(hypothesis)
        return hypothesis

    def register_feature_for_hypothesis(
        self,
        hypothesis_id: str,
        feature_name: str,
        source: str,
        formula: str,
        parameters: dict[str, str | int | float | bool] | None = None,
        methodology: str = "unknown",
        source_claim_id: str = "",
    ) -> ProvenanceRecord:
        h = self.hypothesis_engine.get(hypothesis_id)
        if h is None:
            raise KeyError(f"Hypothesis {hypothesis_id} not found")
        record = ProvenanceRecord(
            feature_name=feature_name,
            source=source,
            formula=formula,
            parameters=parameters or {},
            methodology=methodology,
            source_claim_id=source_claim_id or (h.source_claim_ids[0] if h.source_claim_ids else ""),
        )
        self.provenance_registry.register(record)
        if feature_name not in h.feature_requirements:
            h.feature_requirements = h.feature_requirements + [feature_name]
        return record

    def get_hypothesis_features(self, hypothesis_id: str) -> list[ProvenanceRecord]:
        h = self.hypothesis_engine.get(hypothesis_id)
        if h is None:
            return []
        result: list[ProvenanceRecord] = []
        for fn in h.feature_requirements:
            rec = self.provenance_registry.get(fn)
            if rec is not None:
                result.append(rec)
        return result

    def mark_implementable(self, hypothesis_id: str) -> None:
        h = self.hypothesis_engine.get(hypothesis_id)
        if h is None:
            raise KeyError(f"Hypothesis {hypothesis_id} not found")
        if not h.feature_requirements:
            self.hypothesis_engine.mark_not_implementable(
                hypothesis_id, "No feature requirements defined"
            )
            return
        all_registered = all(
            self.provenance_registry.has_feature(fn) for fn in h.feature_requirements
        )
        if all_registered:
            self.hypothesis_engine.mark_implementable(hypothesis_id, h.feature_requirements)
        else:
            missing = [
                fn for fn in h.feature_requirements
                if not self.provenance_registry.has_feature(fn)
            ]
            self.hypothesis_engine.mark_not_implementable(
                hypothesis_id, f"Missing features: {missing}"
            )
