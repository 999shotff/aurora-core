"""
LLM-4: Investigation Comparison — deterministic current vs historical evidence comparison.

Numerical comparisons MUST be deterministic.
The LLM may explain the comparison but must not replace numerical calculation.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import logging
from typing import Any

from aurora.investigation.schemas import (
    ComparisonChangeType,
    ComparisonDelta,
    InvestigationComparison,
)

logger = logging.getLogger("aurora.investigation.comparison")


def compare_deterministic(
    baseline: dict[str, Any],
    current: dict[str, Any],
    numeric_fields: list[str] | None = None,
) -> InvestigationComparison:
    """
    Create a deterministic comparison between baseline and current data.

    Args:
        baseline: Previous observation or analysis data
        current: Current observation or analysis data
        numeric_fields: Fields to compute numeric deltas for

    Returns:
        InvestigationComparison with deterministic deltas
    """
    if numeric_fields is None:
        numeric_fields = _infer_numeric_fields(baseline, current)

    deltas: list[ComparisonDelta] = []
    all_keys = set(baseline.keys()) | set(current.keys())

    for key in sorted(all_keys):
        bval = baseline.get(key)
        cval = current.get(key)

        if key in ("timestamp", "created_at", "updated_at", "observed_at"):
            continue

        if bval is None and cval is not None:
            deltas.append(ComparisonDelta(
                field_name=key,
                baseline_value=None,
                current_value=cval,
                delta=cval,
                change_type=ComparisonChangeType.NEW,
            ))
        elif bval is not None and cval is None:
            deltas.append(ComparisonDelta(
                field_name=key,
                baseline_value=bval,
                current_value=None,
                delta=None,
                change_type=ComparisonChangeType.MISSING,
            ))
        elif key in numeric_fields:
            delta = _compute_numeric_delta(key, bval, cval)
            deltas.append(delta)
        elif bval != cval:
            deltas.append(ComparisonDelta(
                field_name=key,
                baseline_value=bval,
                current_value=cval,
                delta=None,
                change_type=ComparisonChangeType.CONFLICTING,
            ))
        else:
            deltas.append(ComparisonDelta(
                field_name=key,
                baseline_value=bval,
                current_value=cval,
                delta=0,
                change_type=ComparisonChangeType.UNCHANGED,
            ))

    return InvestigationComparison(
        deltas=deltas,
        unchanged=[d.field_name for d in deltas if d.change_type == ComparisonChangeType.UNCHANGED],
        new_items=[d.field_name for d in deltas if d.change_type == ComparisonChangeType.NEW],
        missing_items=[d.field_name for d in deltas if d.change_type == ComparisonChangeType.MISSING],
        conflicts=[d.field_name for d in deltas if d.change_type == ComparisonChangeType.CONFLICTING],
    )


def _compute_numeric_delta(
    field_name: str, baseline: Any, current: Any
) -> ComparisonDelta:
    """Compute deterministic numeric delta."""
    try:
        b = float(baseline)
        c = float(current)
        delta = round(c - b, 8)
        if abs(delta) < 1e-10:
            change_type = ComparisonChangeType.UNCHANGED
        elif delta > 0:
            change_type = ComparisonChangeType.INCREASED
        else:
            change_type = ComparisonChangeType.DECREASED

        return ComparisonDelta(
            field_name=field_name,
            baseline_value=b,
            current_value=c,
            delta=delta,
            change_type=change_type,
        )
    except (ValueError, TypeError):
        if baseline != current:
            return ComparisonDelta(
                field_name=field_name,
                baseline_value=baseline,
                current_value=current,
                change_type=ComparisonChangeType.CONFLICTING,
            )
        return ComparisonDelta(
            field_name=field_name,
            baseline_value=baseline,
            current_value=current,
            delta=0,
            change_type=ComparisonChangeType.UNCHANGED,
        )


def _infer_numeric_fields(
    baseline: dict[str, Any], current: dict[str, Any]
) -> list[str]:
    """Infer which fields are numeric from the data."""
    numeric: list[str] = []
    all_keys = set(baseline.keys()) | set(current.keys())
    for key in all_keys:
        val = baseline.get(key, current.get(key))
        if isinstance(val, (int, float)):
            numeric.append(key)
    return numeric
