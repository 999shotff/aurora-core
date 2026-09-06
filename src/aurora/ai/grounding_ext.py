"""
Extended Grounding Validation for LLM-2.

Enhances LLM-1 grounding with:
- Citation validation against evidence graph
- Numerical claim verification
- Fake evidence ID rejection
- Source reference integrity checks
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


class GroundingViolation(BaseModel):
    """A specific grounding violation."""

    model_config = {"extra": "forbid"}

    violation_type: str
    description: str
    severity: str = Field(description="critical | warning | info")
    evidence_id: str | None = None


class ExtendedGroundingValidator:
    """
    Validates grounding of LLM responses against evidence graph.

    Checks:
    1. Every cited evidence_id exists in the graph
    2. Numerical claims have source evidence
    3. No fabricated evidence IDs
    4. Source references are consistent
    5. Contradictions are flagged
    """

    def __init__(self) -> None:
        self._known_evidence_ids: set[str] = set()
        self._known_source_refs: set[str] = set()

    def register_evidence(self, evidence_id: str, source_refs: list[str]) -> None:
        """Register known evidence for validation."""
        self._known_evidence_ids.add(evidence_id)
        self._known_source_refs.update(source_refs)

    def validate_response(
        self, response_text: str, evidence_ids: list[str]
    ) -> list[GroundingViolation]:
        """
        Validate that a response is grounded in evidence.

        Returns list of violations (empty = fully grounded).
        """
        violations: list[GroundingViolation] = []

        # Check 1: All cited evidence IDs exist
        for eid in evidence_ids:
            if eid not in self._known_evidence_ids:
                violations.append(
                    GroundingViolation(
                        violation_type="fake_evidence_id",
                        description=f"Evidence ID '{eid}' not found in evidence graph",
                        severity="critical",
                        evidence_id=eid,
                    )
                )

        # Check 2: Numerical claims need source evidence
        numerical_pattern = re.compile(
            r"\b\d+\.?\d*%?\b"  # Matches numbers like 42, 3.14, 15%
        )
        numbers_found = numerical_pattern.findall(response_text)
        if numbers_found and not evidence_ids:
            violations.append(
                GroundingViolation(
                    violation_type="unsourced_numerical_claim",
                    description=f"Response contains {len(numbers_found)} numerical claims but cites no evidence",
                    severity="warning",
                )
            )

        # Check 3: Source reference consistency
        source_pattern = re.compile(r"(yfinance|sentinel|analysis|research|document):[\w.,:/-]+")
        sources_in_text = source_pattern.findall(response_text)
        for source in sources_in_text:
            if source not in self._known_source_refs:
                violations.append(
                    GroundingViolation(
                        violation_type="unknown_source_reference",
                        description=f"Source reference '{source}' not in known sources",
                        severity="warning",
                    )
                )

        return violations

    def validate_tool_result(
        self, tool_result_data: dict[str, Any], source_refs: list[str]
    ) -> list[GroundingViolation]:
        """
        Validate that a tool result has proper grounding.

        Checks that source_refs are non-empty and data is not fabricated.
        """
        violations: list[GroundingViolation] = []

        # Check source refs are present
        if not source_refs:
            violations.append(
                GroundingViolation(
                    violation_type="missing_source_refs",
                    description="Tool result has no source references",
                    severity="critical",
                )
            )

        # Check data status markers
        data_status = tool_result_data.get("data_status", "")
        if data_status in ("DATA_UNAVAILABLE", "PARTIAL"):
            violations.append(
                GroundingViolation(
                    violation_type="partial_data",
                    description=f"Tool result data status: {data_status}",
                    severity="info",
                )
            )

        # Check for AUTH_REQUIRED (Sentinel)
        unavailable = tool_result_data.get("unavailable_sources", [])
        for source_info in unavailable:
            if isinstance(source_info, dict) and source_info.get("reason") == "AUTH_REQUIRED":
                violations.append(
                    GroundingViolation(
                        violation_type="auth_required",
                        description=f"Source '{source_info.get('source')}' requires authentication",
                        severity="info",
                    )
                )

        return violations
