from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Outcome = Literal["up", "down", "flat", "unknown", "abstain"]


class EvaluationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    experiment_id: str
    model_id: str
    timestamp: datetime
    predicted_outcome: Outcome
    predicted_probability: float = Field(ge=0.0, le=1.0)
    actual_outcome: Outcome
    brier_score: float | None = None
    correct: bool | None = None
    market_regime: str = "unknown"
    data_split: Literal["train", "validation", "test", "shadow"]
