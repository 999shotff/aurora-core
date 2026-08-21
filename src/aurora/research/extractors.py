from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aurora.research.schema import (
    DocumentStructure,
    ExtractionError,
    PageContent,
    SectionContent,
)


def extract_txt(path: Path) -> tuple[DocumentStructure, list[ExtractionError]]:
    errors: list[ExtractionError] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        errors.append(
            ExtractionError(error_type="decode_error", message=str(e), timestamp=_now())
        )
        return DocumentStructure(), errors

    lines = text.split("\n")
    pages = [PageContent(page_number=1, text=text, char_count=len(text))]
    sections = _detect_sections_from_lines(lines, page_number=1)
    paragraphs = [l for l in lines if l.strip()]

    return DocumentStructure(
        pages=pages,
        sections=sections,
        total_paragraphs=len(paragraphs),
    ), errors


def extract_markdown(path: Path) -> tuple[DocumentStructure, list[ExtractionError]]:
    errors: list[ExtractionError] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        errors.append(
            ExtractionError(error_type="decode_error", message=str(e), timestamp=_now())
        )
        return DocumentStructure(), errors

    lines = text.split("\n")
    pages = [PageContent(page_number=1, text=text, char_count=len(text))]
    sections = _detect_sections_from_lines(lines, page_number=1)
    paragraphs = [l for l in lines if l.strip()]

    return DocumentStructure(
        pages=pages,
        sections=sections,
        total_paragraphs=len(paragraphs),
    ), errors


def extract_json(path: Path) -> tuple[DocumentStructure, list[ExtractionError]]:
    errors: list[ExtractionError] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        errors.append(
            ExtractionError(error_type="decode_error", message=str(e), timestamp=_now())
        )
        return DocumentStructure(), errors

    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        errors.append(
            ExtractionError(error_type="json_parse_error", message=str(e), timestamp=_now())
        )

    pages = [PageContent(page_number=1, text=text, char_count=len(text))]
    return DocumentStructure(pages=pages, total_paragraphs=1), errors


def extract_pdf(path: Path) -> tuple[DocumentStructure, list[ExtractionError]]:
    errors: list[ExtractionError] = []
    pages: list[PageContent] = []
    sections: list[SectionContent] = []

    try:
        from pypdf import PdfReader
    except ImportError as e:
        errors.append(
            ExtractionError(error_type="import_error", message=str(e), timestamp=_now())
        )
        return DocumentStructure(), errors

    try:
        reader = PdfReader(str(path))
    except (FileNotFoundError, ValueError) as e:
        errors.append(
            ExtractionError(error_type="pdf_open_error", message=str(e), timestamp=_now())
        )
        return DocumentStructure(), errors

    total_paragraphs = 0
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
            pages.append(
                PageContent(page_number=i, text=text, char_count=len(text))
            )
            para_lines = [l for l in text.split("\n") if l.strip()]
            total_paragraphs += len(para_lines)
            sections.extend(_detect_sections_from_lines(para_lines, page_number=i))
        except (AttributeError, TypeError) as e:
            pages.append(
                PageContent(
                    page_number=i,
                    text="",
                    char_count=0,
                    extraction_ok=False,
                    error=str(e),
                )
            )
            errors.append(
                ExtractionError(
                    page_number=i,
                    error_type="page_extract_error",
                    message=str(e),
                    timestamp=_now(),
                )
            )

    return DocumentStructure(
        pages=pages,
        sections=sections,
        total_paragraphs=total_paragraphs,
    ), errors


def _detect_sections_from_lines(
    lines: list[str], page_number: int
) -> list[SectionContent]:
    sections: list[SectionContent] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            level = 0
            for ch in stripped:
                if ch == "#":
                    level += 1
                else:
                    break
            heading = stripped.lstrip("#").strip()
            if heading:
                sections.append(
                    SectionContent(
                        heading=heading,
                        page_number=page_number,
                        paragraph_count=0,
                    )
                )
    return sections


def _now() -> datetime:
    return datetime.now(timezone.utc)

