from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from aurora.hypothesis.metrics import EvaluationMetrics


class ExperimentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    experiment_id: str
    hypothesis_id: str
    dataset_version: str = ""
    feature_version: str = ""
    model: str = ""
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)
    temporal_split: str = ""
    metrics: EvaluationMetrics = Field(default_factory=EvaluationMetrics)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    code_version: str = "0.1.0"
    status: str = "pending"
    notes: str = ""


class ExperimentFamily(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    family_id: str
    description: str = ""
    experiment_ids: list[str] = Field(default_factory=list)
    hypothesis_ids: list[str] = Field(default_factory=list)
    total_experiments: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ExperimentRegistry:
    records: dict[str, ExperimentRecord] = field(default_factory=dict)
    families: dict[str, ExperimentFamily] = field(default_factory=dict)

    def register(self, record: ExperimentRecord) -> None:
        self.records[record.experiment_id] = record
        for fam in self.families.values():
            if record.hypothesis_id in fam.hypothesis_ids and record.experiment_id not in fam.experiment_ids:
                fam.experiment_ids.append(record.experiment_id)
                fam.total_experiments = len(fam.experiment_ids)

    def get(self, experiment_id: str) -> ExperimentRecord | None:
        return self.records.get(experiment_id)

    def list_all(self) -> list[ExperimentRecord]:
        return list(self.records.values())

    def list_by_hypothesis(self, hypothesis_id: str) -> list[ExperimentRecord]:
        return [r for r in self.records.values() if r.hypothesis_id == hypothesis_id]

    def list_by_status(self, status: str) -> list[ExperimentRecord]:
        return [r for r in self.records.values() if r.status == status]

    def count(self) -> int:
        return len(self.records)

    def register_family(self, family: ExperimentFamily) -> None:
        self.families[family.family_id] = family

    def get_family(self, family_id: str) -> ExperimentFamily | None:
        return self.families.get(family_id)

    def list_families(self) -> list[ExperimentFamily]:
        return list(self.families.values())

    def best_by_metric(
        self, metric_name: str, hypothesis_id: str | None = None, higher_is_better: bool = True
    ) -> ExperimentRecord | None:
        candidates = self.list_all()
        if hypothesis_id:
            candidates = [r for r in candidates if r.hypothesis_id == hypothesis_id]
        if not candidates:
            return None
        best = None
        best_val = None
        for r in candidates:
            val = getattr(r.metrics, metric_name, None)
            if val is None:
                continue
            if best_val is None or higher_is_better and val > best_val or not higher_is_better and val < best_val:
                best_val = val
                best = r
        return best
