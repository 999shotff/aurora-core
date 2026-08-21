"""Source-grounding validator and LLM output security.

Treats LLM output as untrusted data.
Validates schema, source grounding, allowed enums, confidence ranges.
"""
from __future__ import annotations

from aurora.research.llm_schema import (
    VALID_CLAIM_TYPES,
    VALID_DIRECTIONS,
    VALID_HORIZONS,
    VALID_METHODLOGIES,
    LLMCandidateClaim,
    LLMExtractionResponse,
    ValidatedClaim,
)


def _source_text_present(source_text: str, original_text: str) -> bool:
    if not source_text or not original_text:
        return False
    normalized_source = " ".join(source_text.lower().split())
    normalized_original = " ".join(original_text.lower().split())
    if normalized_source in normalized_original:
        return True
    source_words = set(normalized_source.split())
    original_words = set(normalized_original.split())
    if not source_words:
        return False
    overlap = len(source_words & original_words) / len(source_words)
    return overlap > 0.7


def validate_candidate(
    candidate: LLMCandidateClaim,
    original_text: str = "",
    document_id: str = "",
    page_number: int = 0,
) -> ValidatedClaim:
    errors: list[str] = []

    if not candidate.exact_source_text.strip():
        errors.append("empty_source_text")

    claim_type = candidate.claim_type
    if claim_type not in VALID_CLAIM_TYPES:
        errors.append(f"invalid_claim_type: {claim_type}")
        claim_type = "unknown"

    methodology = candidate.methodology
    if methodology not in VALID_METHODLOGIES:
        errors.append(f"invalid_methodology: {methodology}")
        methodology = "unknown"

    confidence = candidate.confidence
    if not (0.0 <= confidence <= 1.0):
        errors.append(f"invalid_confidence: {confidence}")
        confidence = 0.5

    horizon = candidate.horizon
    if horizon not in VALID_HORIZONS:
        errors.append(f"invalid_horizon: {horizon}")
        horizon = "unknown"

    direction = candidate.direction
    if direction not in VALID_DIRECTIONS:
        errors.append(f"invalid_direction: {direction}")
        direction = "unknown"

    source_grounded = False
    hallucinated = False
    if original_text:
        source_grounded = _source_text_present(candidate.exact_source_text, original_text)
        if not source_grounded:
            errors.append("source_not_grounded")
            hallucinated = True

    if len(candidate.exact_source_text) > 5000:
        errors.append("source_text_too_long")

    if len(candidate.claim_text) > 2000:
        errors.append("claim_text_too_long")

    return ValidatedClaim(
        source_document_id=candidate.source_document_id or document_id,
        page_number=candidate.page_number or page_number,
        exact_source_text=candidate.exact_source_text,
        claim_type=claim_type,
        methodology=methodology,
        claim_text=candidate.claim_text or candidate.exact_source_text,
        condition=candidate.condition,
        expected_effect=candidate.expected_effect,
        target_variable=candidate.target_variable,
        horizon=horizon,
        direction=direction,
        confidence=confidence,
        extraction_notes=candidate.extraction_notes,
        validation_errors=errors,
        is_valid=len(errors) == 0,
        source_grounded=source_grounded,
        hallucinated=hallucinated,
    )


def validate_response(
    response: LLMExtractionResponse,
    original_text: str = "",
    document_id: str = "",
    page_number: int = 0,
) -> list[ValidatedClaim]:
    validated: list[ValidatedClaim] = []
    for candidate in response.candidate_claims:
        v = validate_candidate(
            candidate,
            original_text=original_text,
            document_id=document_id,
            page_number=page_number,
        )
        validated.append(v)
    return validated


def is_valid_response(response: LLMExtractionResponse) -> bool:
    if not isinstance(response.candidate_claims, list):
        return False
    for claim in response.candidate_claims:
        if not isinstance(exact := getattr(claim, "exact_source_text", None), str):
            return False
        if not exact.strip():
            return False
    return True
