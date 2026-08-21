from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from aurora.research.ocr import OCRProvider, OCRResult, get_ocr_provider


class PageQualityPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_text_length_good: int = 50
    min_text_length_partial: int = 10
    auto_ocr_threshold: int = 0
    enable_ocr: bool = True


class OCRPageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str
    page_number: int
    original_text_length: int = Field(ge=0)
    ocr_text_length: int = Field(ge=0)
    ocr_result: OCRResult | None = None
    action_taken: str = "none"


def classify_page_quality(
    text: str,
    extraction_ok: bool,
    policy: PageQualityPolicy | None = None,
) -> str:
    if policy is None:
        policy = PageQualityPolicy()

    if not extraction_ok:
        return "failed"

    text_len = len(text.strip())
    if text_len >= policy.min_text_length_good:
        return "good"
    if text_len >= policy.min_text_length_partial:
        return "partial"
    if text_len > 0:
        return "partial"
    return "ocr_required"


def should_ocr(
    quality: str,
    text_length: int,
    policy: PageQualityPolicy | None = None,
) -> bool:
    if policy is None:
        policy = PageQualityPolicy()
    if not policy.enable_ocr:
        return False
    if quality == "ocr_required":
        return True
    return quality == "partial" and text_length < policy.auto_ocr_threshold


def ocr_page(
    pdf_path: Path,
    page_number: int,
    document_id: str,
    original_text: str,
    original_quality: str,
    provider: OCRProvider | None = None,
    language: str = "eng",
    output_dir: Path | None = None,
) -> OCRPageResult:
    if provider is None:
        provider = get_ocr_provider()

    if not provider.is_available():
        return OCRPageResult(
            document_id=document_id,
            page_number=page_number,
            original_text_length=len(original_text),
            ocr_text_length=0,
            action_taken="skipped_unavailable",
        )

    try:
        from pdf2image import convert_from_path

        images = convert_from_path(
            str(pdf_path),
            first_page=page_number,
            last_page=page_number,
            dpi=300,
        )
        if not images:
            return OCRPageResult(
                document_id=document_id,
                page_number=page_number,
                original_text_length=len(original_text),
                ocr_text_length=0,
                action_taken="failed_no_image",
            )

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            images[0].save(tmp.name, "PNG")
            tmp_path = Path(tmp.name)

        try:
            ocr_text, confidence = provider.ocr_image(tmp_path, language=language)
        finally:
            tmp_path.unlink(missing_ok=True)

        result = OCRResult(
            document_id=document_id,
            page_number=page_number,
            original_status=original_quality,  # type: ignore[arg-type]
            ocr_text=ocr_text,
            ocr_status="success",
            ocr_engine=provider.engine_name(),
            ocr_version=provider.engine_version(),
            confidence=confidence,
            char_count=len(ocr_text),
        )

        if output_dir:
            ocr_dir = output_dir / "ocr"
            ocr_dir.mkdir(parents=True, exist_ok=True)
            out_path = ocr_dir / f"{document_id}_p{page_number}.json"
            out_path.write_text(
                __import__("json").dumps(result.model_dump(mode="json"), indent=2),
                encoding="utf-8",
            )

        return OCRPageResult(
            document_id=document_id,
            page_number=page_number,
            original_text_length=len(original_text),
            ocr_text_length=len(ocr_text),
            ocr_result=result,
            action_taken="ocr_completed",
        )

    except (ImportError, OSError, ValueError) as e:
        return OCRPageResult(
            document_id=document_id,
            page_number=page_number,
            original_text_length=len(original_text),
            ocr_text_length=0,
            action_taken=f"failed_error: {e}",
        )
