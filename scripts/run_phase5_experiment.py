"""Phase 5 experiment runner.

Benchmarks rule-based, LLM, and hybrid pipelines
on the curated gold-standard dataset.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

_AURORA_ROOT = Path(__file__).resolve().parent.parent
_SRC = _AURORA_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aurora.research.evaluation import EvalMetrics
from aurora.research.gold_standard import GOLD_STANDARD_CASES, get_gold_standard_by_group
from aurora.research.model_adapter import ResearchExtractionModel
from aurora.research.pipelines import (
    HybridPipeline,
    LLMPipeline,
    RuleBasedPipeline,
    run_experiment,
)
from aurora.research.stub_llm import StubLLMModel


def get_llm_model() -> ResearchExtractionModel:
    try:
        from aurora.research.llm_model import LocalLLMModel
        m = LocalLLMModel(model_id="deepseek-r1-distill-qwen-1.5b")
        if m.is_available():
            return m
    except Exception:
        pass
    return StubLLMModel()


def run_benchmark() -> dict[str, EvalMetrics]:
    cases = GOLD_STANDARD_CASES
    gold_dicts = []
    for case in cases:
        gold_dicts.append({
            "text": case.text,
            "document_id": case.document_id,
            "page_number": case.page_number,
            "source_file": case.source_file,
            "expected_methodology": case.expected_methodology,
            "expected_claim_type": case.expected_claim_type,
            "exact_source_text": case.expected_claims[0]["exact_source_text"] if case.expected_claims else case.text[:200],
        })

    rule_pipe = RuleBasedPipeline()
    llm_model = get_llm_model()
    llm_pipe = LLMPipeline(llm_model)
    hybrid_pipe = HybridPipeline(rule_pipe, llm_pipe)

    pipelines = {
        "rule_based": rule_pipe,
        "llm": llm_pipe,
        "hybrid": hybrid_pipe,
    }
    results = run_experiment(gold_dicts, pipelines)
    return results


def run_benchmark_by_group() -> dict[str, dict[str, EvalMetrics]]:
    groups = get_gold_standard_by_group()
    results_by_group: dict[str, dict[str, EvalMetrics]] = {}
    for group_name, cases in groups.items():
        gold_dicts = []
        for case in cases:
            gold_dicts.append({
                "text": case.text,
                "document_id": case.document_id,
                "page_number": case.page_number,
                "source_file": case.source_file,
                "expected_methodology": case.expected_methodology,
                "expected_claim_type": case.expected_claim_type,
                "exact_source_text": case.expected_claims[0]["exact_source_text"] if case.expected_claims else case.text[:200],
            })
        rule_pipe = RuleBasedPipeline()
        llm_model = get_llm_model()
        llm_pipe = LLMPipeline(llm_model)
        hybrid_pipe = HybridPipeline(rule_pipe, llm_pipe)
        pipelines = {
            "rule_based": rule_pipe,
            "llm": llm_pipe,
            "hybrid": hybrid_pipe,
        }
        results_by_group[group_name] = run_experiment(gold_dicts, pipelines)
    return results_by_group


def main() -> None:
    print("=" * 60)
    print("PHASE 5 — CONTROLLED LLM EXTRACTION EXPERIMENT")
    print("=" * 60)
    print()

    print("Loading gold-standard benchmark...")
    cases = GOLD_STANDARD_CASES
    print(f"  Benchmark size: {len(cases)} cases")
    groups = get_gold_standard_by_group()
    print(f"  Methodology groups: {len(groups)}")
    for g, cs in sorted(groups.items()):
        print(f"    {g}: {len(cs)} cases")
    print()

    print("Running benchmark...")
    start = time.time()
    results = run_benchmark()
    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.1f}s")
    print()

    print("=" * 60)
    print("RESULTS BY PIPELINE")
    print("=" * 60)
    for pipe_name, metrics in results.items():
        s = metrics.summary()
        print(f"\n--- {pipe_name.upper()} ---")
        for k, v in s.items():
            print(f"  {k}: {v}")

    print()
    print("=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)
    best = max(results.items(), key=lambda x: x[1].f1)
    print(f"  Best F1: {best[0]} ({best[1].f1:.4f})")
    print()
    print("Do NOT claim any methodology predicts markets.")
    print("Do NOT start backtesting automatically.")
    print()
    print("Phase 5 experiment complete.")


if __name__ == "__main__":
    main()
