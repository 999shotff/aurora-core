"""Feature candidate registry for future AI training."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class EvidenceStatus(Enum):
    UNSUPPORTED = "unsupported"
    WEAK = "weak"
    SUPPORTED = "supported"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"
    EXPERIMENTAL = "experimental"


@dataclass(frozen=True)
class FeatureCandidate:
    feature_id: str
    methodology: str
    hypothesis_id: str
    evidence_status: EvidenceStatus
    oos_directional_accuracy: float
    oos_mean_return: float
    oos_sharpe: float
    robustness_score: float
    dataset_coverage: tuple[str, ...]
    implementation_version: str
    source_claim_id: str
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "feature_id": self.feature_id,
            "methodology": self.methodology,
            "hypothesis_id": self.hypothesis_id,
            "evidence_status": self.evidence_status.value,
            "oos_directional_accuracy": self.oos_directional_accuracy,
            "oos_mean_return": self.oos_mean_return,
            "oos_sharpe": self.oos_sharpe,
            "robustness_score": self.robustness_score,
            "dataset_coverage": list(self.dataset_coverage),
            "implementation_version": self.implementation_version,
            "source_claim_id": self.source_claim_id,
            "registered_at": self.registered_at.isoformat(),
        }


@dataclass
class CandidateRegistry:
    candidates: dict[str, FeatureCandidate] = field(default_factory=dict)

    def register(self, candidate: FeatureCandidate) -> None:
        self.candidates[candidate.feature_id] = candidate

    def get(self, feature_id: str) -> FeatureCandidate | None:
        return self.candidates.get(feature_id)

    def all_ids(self) -> list[str]:
        return list(self.candidates.keys())

    def count(self) -> int:
        return len(self.candidates)

    def by_status(self, status: EvidenceStatus) -> list[FeatureCandidate]:
        return [c for c in self.candidates.values() if c.evidence_status == status]

    def by_methodology(self, methodology: str) -> list[FeatureCandidate]:
        return [c for c in self.candidates.values() if c.methodology == methodology]
