from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ClaimType = Literal[
    "definition",
    "observation",
    "rule",
    "hypothesis",
    "empirical_claim",
    "formula",
    "historical_claim",
    "opinion",
    "unknown",
]

ValidationStatus = Literal["unreviewed", "rejected", "accepted"]

ExtractionMethod = Literal["rule_based", "llm", "hybrid", "manual", "ocr"]

SourceHash = str


class ResearchClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    claim_id: str
    document_id: str
    page: int = Field(ge=1)
    source_text: str
    normalized_text: str
    claim_type: ClaimType
    methodology: str = "unknown"
    methodology_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    methodology_evidence: list[str] = Field(default_factory=list)
    extraction_method: ExtractionMethod = "rule_based"
    extraction_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    validation_status: ValidationStatus = "unreviewed"
    source_file: str = ""
    source_sha256: str = ""
    source_hash: str = ""
    char_offset_start: int | None = None
    char_offset_end: int | None = None
    section_heading: str = ""
    preceding_context: str = ""
    following_context: str = ""
    page_title: str = ""
    is_ocr_derived: bool = False
    ocr_engine: str = ""
    ocr_confidence: float = Field(ge=0.0, le=100.0, default=0.0)
    native_text_quality: str = ""
    ocr_text_quality: str = ""
    selected_text_source: str = "native"
    extraction_version: str = "1.0.0"
    extraction_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class ClaimExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str
    source_file: str
    source_sha256: str
    total_pages: int = Field(ge=0)
    pages_processed: int = Field(ge=0)
    native_pages: int = Field(ge=0, default=0)
    ocr_pages: int = Field(ge=0, default=0)
    claims_extracted: int = Field(ge=0)
    native_claims: int = Field(ge=0, default=0)
    ocr_claims: int = Field(ge=0, default=0)
    hypotheses_extracted: int = Field(ge=0)
    formulas_extracted: int = Field(ge=0)
    ocr_derived_claims: int = Field(ge=0)
    extraction_failures: int = Field(ge=0)
    extraction_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    claims_by_type: dict[str, int] = Field(default_factory=dict)
    claims_by_methodology: dict[str, int] = Field(default_factory=dict)
    duplicate_candidates: int = Field(ge=0, default=0)
