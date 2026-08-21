from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ImplementationStatus = Literal["not_implemented", "implemented", "validated", "rejected"]


class FormulaVariable(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str = ""
    units: str = ""
    default_value: float | None = None
    min_value: float | None = None
    max_value: float | None = None


class ResearchFormula(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    formula_id: str
    source_claim_id: str
    document_id: str
    expression: str
    variables: list[FormulaVariable] = Field(default_factory=list)
    units: str = ""
    assumptions: list[str] = Field(default_factory=list)
    page: int = Field(ge=1)
    implementation_status: ImplementationStatus = "not_implemented"
    extraction_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)
