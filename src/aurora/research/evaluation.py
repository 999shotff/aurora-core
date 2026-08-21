"""Evaluation metrics for controlled LLM extraction experiment.

Metrics:
- claim precision / recall
- methodology accuracy
- claim-type accuracy
- source-text fidelity
- hallucination rate
- UNKNOWN rate
- structured-output validity
- extraction latency
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvalMetrics:
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    methodology_accuracy: float = 0.0
    claim_type_accuracy: float = 0.0
    source_fidelity: float = 0.0
    hallucination_rate: float = 0.0
    unknown_rate: float = 0.0
    structured_output_validity: float = 0.0
    total_extracted: int = 0
    total_expected: int = 0
    correct_methodology: int = 0
    correct_claim_type: int = 0
    grounded_claims: int = 0
    hallucinated_claims: int = 0
    valid_outputs: int = 0
    avg_latency_ms: float = 0.0
    notes: str = ""

    def summary(self) -> dict[str, float | int | str]:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "methodology_accuracy": round(self.methodology_accuracy, 4),
            "claim_type_accuracy": round(self.claim_type_accuracy, 4),
            "source_fidelity": round(self.source_fidelity, 4),
            "hallucination_rate": round(self.hallucination_rate, 4),
            "unknown_rate": round(self.unknown_rate, 4),
            "structured_output_validity": round(self.structured_output_validity, 4),
            "total_extracted": self.total_extracted,
            "total_expected": self.total_expected,
            "correct_methodology": self.correct_methodology,
            "correct_claim_type": self.correct_claim_type,
            "grounded_claims": self.grounded_claims,
            "hallucinated_claims": self.hallucinated_claims,
            "valid_outputs": self.valid_outputs,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


def _source_match(extracted: str, expected: str) -> bool:
    norm_e = " ".join(extracted.lower().split())
    norm_x = " ".join(expected.lower().split())
    if not norm_x:
        return False
    if norm_x in norm_e or norm_e in norm_x:
        return True
    words_e = set(norm_e.split())
    words_x = set(norm_x.split())
    overlap = len(words_e & words_x) / max(len(words_x), 1)
    return overlap > 0.5


def evaluate_predictions(
    predictions: list[dict],
    gold_standard: list[dict],
) -> EvalMetrics:
    tp = 0
    total_pred = len(predictions)
    total_gold = len(gold_standard)
    correct_method = 0
    correct_type = 0
    grounded = 0
    hallucinated = 0
    unknown_count = 0
    valid = 0

    for pred in predictions:
        is_match = False
        for gold in gold_standard:
            if _source_match(pred.get("exact_source_text", ""), gold.get("exact_source_text", "")):
                is_match = True
                if pred.get("methodology") == gold.get("methodology"):
                    correct_method += 1
                if pred.get("claim_type") == gold.get("claim_type"):
                    correct_type += 1
                break
        if is_match:
            tp += 1
        if pred.get("source_grounded", False):
            grounded += 1
        elif not pred.get("is_valid", True):
            hallucinated += 1
        if pred.get("methodology") == "unknown":
            unknown_count += 1
        if pred.get("is_valid", True):
            valid += 1

    precision = tp / total_pred if total_pred > 0 else 0.0
    recall = tp / total_gold if total_gold > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    method_acc = correct_method / total_pred if total_pred > 0 else 0.0
    type_acc = correct_type / total_pred if total_pred > 0 else 0.0
    fidelity = grounded / total_pred if total_pred > 0 else 0.0
    hall_rate = hallucinated / total_pred if total_pred > 0 else 0.0
    unk_rate = unknown_count / total_pred if total_pred > 0 else 0.0
    validity = valid / total_pred if total_pred > 0 else 0.0

    return EvalMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        methodology_accuracy=method_acc,
        claim_type_accuracy=type_acc,
        source_fidelity=fidelity,
        hallucination_rate=hall_rate,
        unknown_rate=unk_rate,
        structured_output_validity=validity,
        total_extracted=total_pred,
        total_expected=total_gold,
        correct_methodology=correct_method,
        correct_claim_type=correct_type,
        grounded_claims=grounded,
        hallucinated_claims=hallucinated,
        valid_outputs=valid,
    )
