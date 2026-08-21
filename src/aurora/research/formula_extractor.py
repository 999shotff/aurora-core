"""Formula extraction from candidate claims.

Extracts mathematical formulas and expressions from research text.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from aurora.research.claims import ResearchClaim
from aurora.research.formulas import FormulaVariable, ResearchFormula

_FORMULA_PATTERNS = [
    re.compile(r"[A-Za-z_]\w*\s*=\s*[^.;]+", re.IGNORECASE),
    re.compile(r"(?:formula|equation|expression|calculate|computation)\s*[:=]\s*[^.;]+", re.IGNORECASE),
    re.compile(r"\b(?:SMA|EMA|RSI|ATR|VWAP|OBV|MACD|ADX|CCI|Williams)\b[^.;]*", re.IGNORECASE),
]

_VARIABLE_PATTERN = re.compile(r"\b([A-Za-z_]\w*)\b")
_COMMON_VARS = {
    "close", "open", "high", "low", "volume", "price", "return", "period",
    "sma", "ema", "rsi", "atr", "vwap", "obv", "macd", "adx", "cci",
}


def _extract_formula_text(sentence: str) -> str | None:
    for pattern in _FORMULA_PATTERNS:
        match = pattern.search(sentence)
        if match:
            return match.group(0).strip()
    return None


def _extract_variables(formula_text: str) -> list[FormulaVariable]:
    tokens = _VARIABLE_PATTERN.findall(formula_text)
    seen: set[str] = set()
    variables: list[FormulaVariable] = []
    for token in tokens:
        lower = token.lower()
        if lower in seen or lower in {"if", "then", "when", "where", "and", "or", "the", "is", "a", "an"}:
            continue
        seen.add(lower)
        if lower in _COMMON_VARS or any(lower.startswith(p) for p in ["sma", "ema", "rsi", "atr"]):
            variables.append(FormulaVariable(
                name=token,
                description=f"Variable {token}",
                units="",
            ))
    return variables


def extract_formula_from_claim(claim: ResearchClaim) -> ResearchFormula | None:
    if claim.claim_type != "formula":
        return None

    formula_text = _extract_formula_text(claim.source_text)
    if not formula_text:
        return None

    variables = _extract_variables(formula_text)

    return ResearchFormula(
        formula_id=f"formula_{claim.claim_id}",
        source_claim_id=claim.claim_id,
        document_id=claim.document_id,
        expression=formula_text,
        variables=variables,
        units="",
        assumptions=[],
        page=claim.page,
        implementation_status="not_implemented",
        extraction_timestamp=datetime.now(timezone.utc),
        notes=f"Extracted from: {claim.normalized_text[:100]}",
    )


def extract_formulas(claims: list[ResearchClaim]) -> list[ResearchFormula]:
    formulas: list[ResearchFormula] = []
    for claim in claims:
        formula = extract_formula_from_claim(claim)
        if formula is not None:
            formulas.append(formula)
    return formulas
