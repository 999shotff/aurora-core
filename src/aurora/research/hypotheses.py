from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TestStatus = Literal["untested", "supported", "weak", "rejected", "conflicting"]
Direction = Literal["long", "short", "neutral", "unknown"]
Horizon = Literal["tick", "intraday", "swing", "position", "unknown"]


class ResearchHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    hypothesis_id: str
    source_claim_id: str
    document_id: str
    methodology: str
    condition: str = ""
    expected_effect: str = ""
    target_variable: str = ""
    horizon: Horizon = "unknown"
    direction: Direction = "unknown"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    test_status: TestStatus = "untested"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)
