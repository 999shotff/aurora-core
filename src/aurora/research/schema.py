from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PageContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_number: int = Field(ge=1)
    text: str
    char_count: int = Field(ge=0)
    extraction_ok: bool = True
    error: str | None = None


class TableContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_number: int = Field(ge=1)
    rows: list[list[str]]
    row_count: int = Field(ge=0)


class SectionContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heading: str
    page_number: int = Field(ge=1)
    paragraph_count: int = Field(ge=0)


class DocumentStructure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pages: list[PageContent] = Field(default_factory=list)
    sections: list[SectionContent] = Field(default_factory=list)
    tables: list[TableContent] = Field(default_factory=list)
    total_paragraphs: int = Field(ge=0, default=0)


class ExtractionError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_number: int | None = None
    error_type: str
    message: str
    timestamp: datetime


class ResearchDocumentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    document_id: str
    filename: str
    source_path: str
    suffix: str
    size_bytes: int
    sha256: str
    page_count: int = Field(ge=0)
    extraction_status: Literal["success", "partial", "failed"]
    extraction_timestamp: datetime
    source_type: Literal["pdf", "txt", "md", "json"]
    text_location: str
    structure: DocumentStructure = Field(default_factory=DocumentStructure)
    errors: list[ExtractionError] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class ResearchIndex(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    version: str = "0.1.0"
    created_at: datetime
    document_count: int = Field(ge=0)
    documents: list[ResearchDocumentRecord] = Field(default_factory=list)
