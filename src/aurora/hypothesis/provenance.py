from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class ProvenanceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    feature_name: str
    source: str
    formula: str
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    methodology: str = "unknown"
    source_claim_id: str = ""
    implementation_version: str = "1.0.0"
    notes: str = ""

    def to_dict(self) -> dict[str, str | int | float | bool | dict[str, str | int | float | bool]]:
        return {
            "feature_name": self.feature_name,
            "source": self.source,
            "formula": self.formula,
            "parameters": self.parameters,
            "timestamp": self.timestamp.isoformat(),
            "methodology": self.methodology,
            "source_claim_id": self.source_claim_id,
            "implementation_version": self.implementation_version,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class FeatureProvenanceRegistry:
    records: dict[str, ProvenanceRecord] = field(default_factory=dict)

    def register(self, record: ProvenanceRecord) -> None:
        self.records[record.feature_name] = record

    def get(self, feature_name: str) -> ProvenanceRecord | None:
        return self.records.get(feature_name)

    def list_all(self) -> list[ProvenanceRecord]:
        return list(self.records.values())

    def list_by_methodology(self, methodology: str) -> list[ProvenanceRecord]:
        return [r for r in self.records.values() if r.methodology == methodology]

    def list_by_source_claim(self, claim_id: str) -> list[ProvenanceRecord]:
        return [r for r in self.records.values() if r.source_claim_id == claim_id]

    def count(self) -> int:
        return len(self.records)

    def has_feature(self, feature_name: str) -> bool:
        return feature_name in self.records
