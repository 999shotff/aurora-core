from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ExtractionQuality = Literal["good", "partial", "failed", "ocr_required", "manual_review"]


class ExtractionQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str
    overall_quality: ExtractionQuality
    total_pages: int = Field(ge=0)
    good_pages: int = Field(ge=0)
    partial_pages: int = Field(ge=0)
    failed_pages: int = Field(ge=0)
    ocr_required_pages: int = Field(ge=0)
    manual_review_pages: int = Field(ge=0)
    can_extract_claims: bool = True
    notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "overall_quality": self.overall_quality,
            "total_pages": self.total_pages,
            "good_pages": self.good_pages,
            "partial_pages": self.partial_pages,
            "failed_pages": self.failed_pages,
            "can_extract_claims": self.can_extract_claims,
        }


def assess_extraction_quality(
    page_qualities: list[ExtractionQuality],
    document_id: str,
) -> ExtractionQualityReport:
    total = len(page_qualities)
    counts: dict[str, int] = {}
    for q in page_qualities:
        counts[q] = counts.get(q, 0) + 1

    good = counts.get("good", 0)
    partial = counts.get("partial", 0)
    failed = counts.get("failed", 0)
    ocr = counts.get("ocr_required", 0)
    manual = counts.get("manual_review", 0)

    if failed > total * 0.5:
        overall: ExtractionQuality = "failed"
        can_extract = False
    elif ocr > total * 0.3:
        overall = "ocr_required"
        can_extract = False
    elif manual > total * 0.3:
        overall = "manual_review"
        can_extract = False
    elif good == total and total > 0:
        overall = "good"
        can_extract = True
    elif good + partial > total * 0.5:
        overall = "partial"
        can_extract = True
    else:
        overall = "partial"
        can_extract = True

    notes: list[str] = []
    if failed > 0:
        notes.append(f"{failed}/{total} pages failed extraction")
    if ocr > 0:
        notes.append(f"{ocr}/{total} pages require OCR")
    if manual > 0:
        notes.append(f"{manual}/{total} pages require manual review")

    return ExtractionQualityReport(
        document_id=document_id,
        overall_quality=overall,
        total_pages=total,
        good_pages=good,
        partial_pages=partial,
        failed_pages=failed,
        ocr_required_pages=ocr,
        manual_review_pages=manual,
        can_extract_claims=can_extract,
        notes=notes,
    )
