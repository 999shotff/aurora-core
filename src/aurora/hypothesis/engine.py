from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

HypothesisStatus = Literal[
    "untested", "implemented", "testing", "supported", "weak", "rejected", "inconclusive"
]

ImplementationStatus = Literal[
    "not_implementable", "not_implemented", "implemented", "validated", "rejected"
]

ValidationVerdict = Literal["pass", "fail", "inconclusive", "not_run"]


class TestableHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    hypothesis_id: str
    source_claim_ids: list[str] = Field(default_factory=list)
    methodology: str
    condition: str = ""
    feature_requirements: list[str] = Field(default_factory=list)
    target: str = ""
    horizon: str = "unknown"
    direction: str = "unknown"
    assumptions: list[str] = Field(default_factory=list)
    implementation_status: ImplementationStatus = "not_implemented"
    validation_status: HypothesisStatus = "untested"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

    def transition_to(self, new_status: HypothesisStatus) -> None:
        allowed_transitions: dict[str, list[str]] = {
            "untested": ["implemented", "rejected"],
            "implemented": ["testing", "rejected"],
            "testing": ["supported", "weak", "rejected", "inconclusive"],
            "supported": ["weak", "rejected"],
            "weak": ["rejected", "supported"],
            "rejected": [],
            "inconclusive": ["testing", "rejected"],
        }
        current_allowed = allowed_transitions.get(self.validation_status, [])
        if new_status not in current_allowed:
            raise ValueError(
                f"Invalid transition: {self.validation_status} -> {new_status}. "
                f"Allowed: {current_allowed}"
            )
        self.validation_status = new_status
        self.updated_at = datetime.now(timezone.utc)


class HypothesisEngine:
    def __init__(self) -> None:
        self._hypotheses: dict[str, TestableHypothesis] = {}

    def register(self, hypothesis: TestableHypothesis) -> None:
        if hypothesis.hypothesis_id in self._hypotheses:
            raise ValueError(f"Hypothesis {hypothesis.hypothesis_id} already registered")
        self._hypotheses[hypothesis.hypothesis_id] = hypothesis

    def get(self, hypothesis_id: str) -> TestableHypothesis | None:
        return self._hypotheses.get(hypothesis_id)

    def list_all(self) -> list[TestableHypothesis]:
        return list(self._hypotheses.values())

    def list_by_status(self, status: HypothesisStatus) -> list[TestableHypothesis]:
        return [h for h in self._hypotheses.values() if h.validation_status == status]

    def list_by_methodology(self, methodology: str) -> list[TestableHypothesis]:
        return [h for h in self._hypotheses.values() if h.methodology == methodology]

    def count(self) -> int:
        return len(self._hypotheses)

    def transition(self, hypothesis_id: str, new_status: HypothesisStatus) -> None:
        h = self._hypotheses.get(hypothesis_id)
        if h is None:
            raise KeyError(f"Hypothesis {hypothesis_id} not found")
        h.transition_to(new_status)

    def mark_implementable(
        self, hypothesis_id: str, feature_requirements: list[str]
    ) -> None:
        h = self._hypotheses.get(hypothesis_id)
        if h is None:
            raise KeyError(f"Hypothesis {hypothesis_id} not found")
        h.feature_requirements = feature_requirements
        h.implementation_status = "implemented"
        h.updated_at = datetime.now(timezone.utc)

    def mark_not_implementable(self, hypothesis_id: str, reason: str = "") -> None:
        h = self._hypotheses.get(hypothesis_id)
        if h is None:
            raise KeyError(f"Hypothesis {hypothesis_id} not found")
        h.implementation_status = "not_implementable"
        if reason:
            h.notes = reason
        h.updated_at = datetime.now(timezone.utc)
