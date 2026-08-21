"""Deterministic rule-based claim extractor for Phase 4.5.

Extracts candidate claims from research text using pattern matching.
No LLM involved — pure deterministic rules.

Phase 4.5 improvements:
- Context-aware methodology classification
- Classification confidence and evidence
- Claim context (preceding/following sentences, section title)
- OCR text routing
- Native/OCR quality comparison
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from aurora.research.claims import ClaimType, ResearchClaim
from aurora.research.models import ResearchPage
from aurora.research.taxonomy import classify_methodology_context

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_IF_THEN = re.compile(r"\bif\b.*?\bthen\b", re.IGNORECASE)
_WHEN_THEN = re.compile(r"\bwhen\b.*?\bthen\b", re.IGNORECASE)
_BUY_SELL = re.compile(
    r"\b(buy|sell|go long|go short|enter|exit|close|open|hold)\b",
    re.IGNORECASE,
)
_ABOVE_BELOW = re.compile(r"\b(above|below|crosses|breaks?|touches?|reaches?)\b", re.IGNORECASE)
_FORMULA = re.compile(r"[A-Za-z_]\w*\s*[=+\-*/^]\s*\d")
_NUMBERED_RULE = re.compile(r"^\s*\d+[\.\)]\s+", re.MULTILINE)
_MEASURABLE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:%|percent|points?|pips?|ticks?|periods?|bars?|days?|weeks?|months?)\b",
    re.IGNORECASE,
)
_DEFINITIONS = re.compile(
    r"\b(is defined as|is the measure of|refers to|means|is calculated as|is given by)\b",
    re.IGNORECASE,
)
_HISTORICAL = re.compile(
    r"\b(in \d{4}|during|historically|since \d{4}|in the past|previous(?:ly)?|last \d+)\b",
    re.IGNORECASE,
)
_OPINION = re.compile(
    r"\b(I believe|I think|in my opinion|arguably|it seems|appears to be|likely|probably)\b",
    re.IGNORECASE,
)
_OBSERVATION = re.compile(
    r"\b(observed|noted|found that|studies show|research indicates|data shows|evidence suggests)\b",
    re.IGNORECASE,
)


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _split_sentences(text: str) -> list[str]:
    parts = _SENTENCE_SPLIT.split(text)
    return [s.strip() for s in parts if len(s.strip()) > 20]


def _classify_claim_type(sentence: str) -> ClaimType:
    if _DEFINITIONS.search(sentence):
        return "definition"
    if _IF_THEN.search(sentence) or _WHEN_THEN.search(sentence):
        return "rule"
    if _BUY_SELL.search(sentence) and (_ABOVE_BELOW.search(sentence) or _IF_THEN.search(sentence)):
        return "rule"
    if _FORMULA.search(sentence):
        return "formula"
    if _HISTORICAL.search(sentence):
        return "historical_claim"
    if _OPINION.search(sentence):
        return "opinion"
    if _OBSERVATION.search(sentence):
        return "observation"
    if _MEASURABLE.search(sentence):
        return "empirical_claim"
    if _NUMBERED_RULE.search(sentence):
        return "rule"
    return "unknown"


def _normalize_text(sentence: str) -> str:
    normalized = re.sub(r"\s+", " ", sentence).strip()
    normalized = re.sub(r"[^\w\s.,;:!?%+\-*/^()='\"/]", "", normalized)
    return normalized


def _find_char_offsets(full_text: str, sentence: str) -> tuple[int | None, int | None]:
    idx = full_text.find(sentence[:80])
    if idx == -1:
        return None, None
    return idx, idx + len(sentence)


def _get_context(
    sentences: list[str], idx: int, window: int = 1,
) -> tuple[str, str]:
    preceding = sentences[max(0, idx - window):idx]
    following = sentences[idx + 1:idx + 1 + window]
    return " ".join(preceding), " ".join(following)


def _build_page_context(page: ResearchPage) -> str:
    parts = []
    text = page.text[:500] if page.text else ""
    if text:
        parts.append(text)
    return " ".join(parts)


def extract_claims_from_page(
    page: ResearchPage,
    document_id: str,
    source_file: str = "",
    source_sha256: str = "",
    extraction_method: str = "rule_based",
    is_ocr: bool = False,
    ocr_engine: str = "",
    ocr_confidence: float = 0.0,
    native_text_quality: str = "",
    ocr_text_quality: str = "",
    selected_text_source: str = "native",
) -> list[ResearchClaim]:
    claims: list[ResearchClaim] = []
    sentences = _split_sentences(page.text)
    page_context = _build_page_context(page)

    for idx, sentence in enumerate(sentences):
        claim_type = _classify_claim_type(sentence)
        if claim_type == "unknown":
            continue

        normalized = _normalize_text(sentence)
        preceding, following = _get_context(sentences, idx)

        class_result = classify_methodology_context(sentence, context=page_context)

        source_hash = _text_hash(normalized)
        offsets = _find_char_offsets(page.text, sentence)

        confidence = 0.5
        if claim_type == "definition":
            confidence = 0.7
        elif claim_type == "rule":
            confidence = 0.6
        elif claim_type == "formula":
            confidence = 0.8
        elif claim_type == "observation":
            confidence = 0.55
        elif claim_type == "empirical_claim" or claim_type == "historical_claim":
            confidence = 0.5
        elif claim_type == "opinion":
            confidence = 0.4

        method: str = extraction_method
        if is_ocr:
            method = "ocr"

        claim = ResearchClaim(
            claim_id=f"{document_id}_p{page.page_number}_c{source_hash[:8]}",
            document_id=document_id,
            page=page.page_number,
            source_text=sentence,
            normalized_text=normalized,
            claim_type=claim_type,
            methodology=class_result.category,
            methodology_confidence=class_result.confidence,
            methodology_evidence=class_result.evidence,
            extraction_method=method,  # type: ignore[arg-type]
            extraction_confidence=confidence,
            validation_status="unreviewed",
            source_file=source_file,
            source_sha256=source_sha256,
            source_hash=source_hash,
            char_offset_start=offsets[0],
            char_offset_end=offsets[1],
            section_heading="",
            preceding_context=preceding[:200],
            following_context=following[:200],
            page_title="",
            is_ocr_derived=is_ocr,
            ocr_engine=ocr_engine,
            ocr_confidence=ocr_confidence,
            native_text_quality=native_text_quality,
            ocr_text_quality=ocr_text_quality,
            selected_text_source=selected_text_source,
        )
        claims.append(claim)

    return claims


def extract_claims_from_document(
    pages: list[ResearchPage],
    document_id: str,
    source_file: str = "",
    source_sha256: str = "",
) -> list[ResearchClaim]:
    all_claims: list[ResearchClaim] = []
    for page in pages:
        page_claims = extract_claims_from_page(
            page=page,
            document_id=document_id,
            source_file=source_file,
            source_sha256=source_sha256,
        )
        all_claims.extend(page_claims)
    return all_claims


def select_text_source(
    native_text: str,
    native_quality: str,
    ocr_text: str,
    ocr_quality: str,
) -> tuple[str, str, str]:
    """Select best text source and return (selected_text, source, reason)."""
    if native_quality == "good" and native_text.strip():
        return native_text, "native", "native_quality_good"
    if ocr_quality == "good" and ocr_text.strip():
        return ocr_text, "ocr", "ocr_quality_good"
    if native_text.strip() and len(native_text) > len(ocr_text):
        return native_text, "native", "native_longer"
    if ocr_text.strip():
        return ocr_text, "ocr", "ocr_available"
    return native_text, "native", "fallback_native"


def load_ocr_results(
    extracted_dir: Path, document_id: str, page_number: int,
) -> dict | None:
    ocr_dir = extracted_dir / "ocr"
    pattern = f"{document_id}_p{page_number}.json"
    ocr_path = ocr_dir / pattern
    if not ocr_path.exists():
        return None
    return json.loads(ocr_path.read_text(encoding="utf-8"))
