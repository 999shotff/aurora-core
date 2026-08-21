"""Experiment pre-registration: store specifications before running."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Classification(Enum):
    SUPPORTED = "supported"
    WEAK = "weak"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class MethodologyFamily(Enum):
    FIBONACCI = "fibonacci"
    VOLATILITY = "volatility"
    TECHNICAL_ANALYSIS = "technical_analysis"
    LIQUIDITY = "liquidity"
    VOLUME = "volume"
    VWAP = "vwap"
    MARKET_STRUCTURE = "market_structure"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    GANN = "gann"
    TIME_CYCLES = "time_cycles"
    ASTROLOGY = "astrology"
    NO_COMPUTABLE_HYPOTHESIS = "no_computable_hypothesis"


@dataclass(frozen=True)
class PreRegistration:
    experiment_id: str
    hypothesis_id: str
    methodology: MethodologyFamily
    hypothesis_text: str
    expected_direction: str
    feature_formula: str
    parameters: dict[str, Any]
    target: str
    horizon_bars: int
    evaluation_metrics: tuple[str, ...]
    baseline: str
    classification_criteria: dict[str, str]
    transaction_cost_bps: float
    source_claim_id: str
    source_document: str
    source_page: int
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis_id": self.hypothesis_id,
            "methodology": self.methodology.value,
            "hypothesis_text": self.hypothesis_text,
            "expected_direction": self.expected_direction,
            "feature_formula": self.feature_formula,
            "parameters": self.parameters,
            "target": self.target,
            "horizon_bars": self.horizon_bars,
            "evaluation_metrics": list(self.evaluation_metrics),
            "baseline": self.baseline,
            "classification_criteria": self.classification_criteria,
            "transaction_cost_bps": self.transaction_cost_bps,
            "source_claim_id": self.source_claim_id,
            "source_document": self.source_document,
            "source_page": self.source_page,
            "registered_at": self.registered_at.isoformat(),
        }


@dataclass
class PreRegistrationLog:
    entries: dict[str, PreRegistration] = field(default_factory=dict)

    def register(self, prereg: PreRegistration) -> None:
        self.entries[prereg.experiment_id] = prereg

    def get(self, experiment_id: str) -> PreRegistration | None:
        return self.entries.get(experiment_id)

    def all_ids(self) -> list[str]:
        return list(self.entries.keys())

    def count(self) -> int:
        return len(self.entries)
