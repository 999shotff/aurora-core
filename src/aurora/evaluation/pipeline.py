from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from aurora.evaluation.metrics import (
    abstention_quality,
    brier_score,
    calibration_error,
    directional_accuracy,
    mean_brier_score,
    outcome_distribution,
)
from aurora.features.base import FeatureVector
from aurora.models.base import ModelAdapter, ModelInput
from aurora.schemas.evaluation import EvaluationRecord, Outcome
from aurora.schemas.market_state import MarketState


@dataclass(frozen=True)
class ExperimentResult:
    experiment_id: str
    model_id: str
    records: list[EvaluationRecord]
    summary: dict[str, Any]
    timestamp: datetime


def _state_to_input(state: MarketState, data_split: str) -> ModelInput:
    """Wrap a MarketState into a ModelInput for the model adapter."""
    fv = FeatureVector(
        version="0.1.0",
        extractor_id="pipeline_passthrough",
        asset=state.asset,
        timeframe=state.timeframe,
        timestamp=state.timestamp,
        numerical={"price": state.price},
    )
    return ModelInput(
        instrument_id=state.asset,
        timeframe=state.timeframe,
        timestamp=state.timestamp,
        feature_vector=fv,
        market_state=state,
        data_quality=state.data_quality,
        feature_schema_version="0.1.0",
        evaluation_context=data_split,
    )


@dataclass(frozen=True)
class EvaluationPipeline:
    experiment_id: str

    def evaluate_model(
        self,
        model: ModelAdapter,
        scenarios: list[MarketState],
        outcomes: list[Outcome],
        data_split: Literal["train", "validation", "test", "shadow"],
    ) -> ExperimentResult:
        if len(scenarios) != len(outcomes):
            raise ValueError(
                f"scenarios ({len(scenarios)}) and outcomes ({len(outcomes)}) length mismatch"
            )

        records: list[EvaluationRecord] = []
        for state, actual in zip(scenarios, outcomes):
            model_input = _state_to_input(state, data_split)
            response = model.predict(model_input)

            correct = directional_accuracy(response.outcome, actual)
            bs = brier_score(response.probability, actual == "up")

            record = EvaluationRecord(
                experiment_id=self.experiment_id,
                model_id=model.model_id,
                timestamp=state.timestamp,
                predicted_outcome=response.outcome,
                predicted_probability=response.probability,
                actual_outcome=actual,
                brier_score=bs,
                correct=correct,
                market_regime=state.volatility.regime,
                data_split=data_split,
            )
            records.append(record)

        summary = self._compute_summary(records)
        return ExperimentResult(
            experiment_id=self.experiment_id,
            model_id=model.model_id,
            records=records,
            summary=summary,
            timestamp=datetime.now(timezone.utc),
        )

    def _compute_summary(self, records: list[EvaluationRecord]) -> dict[str, Any]:
        if not records:
            return {"count": 0}

        bs_pairs = [
            (r.predicted_probability, r.actual_outcome == "up")
            for r in records
        ]
        avg_brier = mean_brier_score(bs_pairs)

        correct_flags = [r.correct for r in records]
        accuracy = (
            sum(1 for c in correct_flags if c) / len(correct_flags)
            if correct_flags
            else 0.0
        )

        abstained = [r.predicted_outcome in ("unknown", "abstain") for r in records]
        aq = abstention_quality(abstained, correct_flags)

        cal = calibration_error(bs_pairs)

        predicted_outcomes: list[str] = [r.predicted_outcome for r in records]
        dist = outcome_distribution(predicted_outcomes)

        return {
            "count": len(records),
            "mean_brier_score": avg_brier,
            "accuracy": accuracy,
            "calibration_error": cal,
            "abstention_rate": aq["abstention_rate"],
            "non_abstain_accuracy": aq["non_abstain_accuracy"],
            "outcome_distribution": dist,
        }

    def save_result(self, result: ExperimentResult, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "experiment_id": result.experiment_id,
            "model_id": result.model_id,
            "timestamp": result.timestamp.isoformat(),
            "summary": result.summary,
            "record_count": len(result.records),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
