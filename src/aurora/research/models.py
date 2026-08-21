from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ExtractionQuality = Literal["good", "partial", "failed", "ocr_required", "manual_review"]
SourceType = Literal["pdf", "txt", "md", "json", "unknown"]


class ResearchSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_path: str
    sha256: str
    source_type: SourceType
    size_bytes: int = Field(ge=0)
    filename: str


class ResearchParagraph(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paragraph_id: str
    document_id: str
    page_number: int = Field(ge=1)
    section_heading: str = ""
    text: str
    char_count: int = Field(ge=0)
    index_in_page: int = Field(ge=0)


class ResearchTable(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table_id: str
    document_id: str
    page_number: int = Field(ge=1)
    rows: list[list[str]]
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)


class ResearchSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_id: str
    document_id: str
    page_number: int = Field(ge=1)
    heading: str
    level: int = Field(ge=1, le=6)
    paragraph_ids: list[str] = Field(default_factory=list)
    table_ids: list[str] = Field(default_factory=list)


class ResearchPage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_id: str
    document_id: str
    page_number: int = Field(ge=1)
    text: str
    char_count: int = Field(ge=0)
    extraction_quality: ExtractionQuality = "good"
    section_ids: list[str] = Field(default_factory=list)
    paragraph_ids: list[str] = Field(default_factory=list)
    table_ids: list[str] = Field(default_factory=list)
    error: str | None = None


class ResearchDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    document_id: str
    title: str = ""
    source: ResearchSource
    page_count: int = Field(ge=0)
    extraction_quality: ExtractionQuality = "good"
    extraction_version: str = "1.0.0"
    extraction_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    page_ids: list[str] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)
    table_ids: list[str] = Field(default_factory=list)
    paragraph_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @property
    def sha256(self) -> str:
        return self.source.sha256
