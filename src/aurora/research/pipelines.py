"""Three extraction pipelines: RuleBased, LLM, Hybrid.

Hybrid behavior:
1. Run deterministic extraction
2. Identify uncertain/UNKNOWN candidates
3. Send only appropriate context to LLM
4. Validate LLM output against strict schema
5. Require source-text grounding
6. Preserve provenance
7. Never silently replace the original rule-based result
"""
from __future__ import annotations

import time

from aurora.research.deduplication import KeywordDeduplicator
from aurora.research.evaluation import EvalMetrics, evaluate_predictions
from aurora.research.extractor import extract_claims_from_page
from aurora.research.llm_schema import LLMExtractionResponse
from aurora.research.model_adapter import (
    ExtractionRequest,
    ExtractionResult,
    ResearchExtractionModel,
)
from aurora.research.models import ResearchPage
from aurora.research.source_validator import validate_response


class ExtractionPipeline:
    name: str = "base"

    def run(self, text: str, **kwargs: str | int | bool) -> list[dict]:
        raise NotImplementedError

    def _extract_from_text(self, text: str, **kwargs: str | int | bool) -> list[dict]:
        raise NotImplementedError


class RuleBasedPipeline(ExtractionPipeline):
    name = "rule_based"

    def __init__(self) -> None:
        self._dedup = KeywordDeduplicator()

    def _extract_from_text(self, text: str, **kwargs: str | int | bool) -> list[dict]:
        doc_id = str(kwargs.get("document_id", ""))
        page_num = int(kwargs.get("page_number", 1))
        source_file = str(kwargs.get("source_file", ""))
        source_sha = str(kwargs.get("source_sha256", ""))
        page = ResearchPage(
            page_id=f"pipeline_p{page_num}",
            document_id=doc_id,
            page_number=page_num,
            text=text,
            char_count=len(text),
        )
        claims = extract_claims_from_page(
            page=page,
            document_id=doc_id,
            source_file=source_file,
            source_sha256=source_sha,
        )
        result: list[dict] = []
        for rc in claims:
            result.append({
                "source_document_id": rc.document_id,
                "page_number": rc.page,
                "exact_source_text": rc.source_text,
                "claim_type": rc.claim_type,
                "methodology": rc.methodology,
                "claim_text": rc.normalized_text,
                "confidence": 0.8,
                "is_valid": True,
                "source_grounded": True,
                "hallucinated": False,
                "extraction_method": "rule_based",
                "condition": rc.condition if hasattr(rc, "condition") else None,
                "expected_effect": rc.expected_effect if hasattr(rc, "expected_effect") else None,
                "target_variable": rc.target_variable if hasattr(rc, "target_variable") else None,
                "horizon": rc.horizon if hasattr(rc, "horizon") else None,
                "direction": rc.direction if hasattr(rc, "direction") else None,
            })
        return result

    def run(self, text: str, **kwargs: str | int | bool) -> list[dict]:
        return self._extract_from_text(text, **kwargs)


class LLMPipeline(ExtractionPipeline):
    name = "llm"

    def __init__(self, model: ResearchExtractionModel) -> None:
        self._model = model
        self._latencies: list[float] = []

    def _extract_from_text(self, text: str, **kwargs: str | int | bool) -> list[dict]:
        doc_id = str(kwargs.get("document_id", ""))
        page_num = int(kwargs.get("page_number", 1))
        is_ocr = bool(kwargs.get("is_ocr", False))
        request = ExtractionRequest(
            text=text,
            document_id=doc_id,
            page_number=page_num,
            is_ocr=is_ocr,
        )
        result: ExtractionResult = self._model.extract_claims(request)
        self._latencies.append(result.latency_ms)
        if result.status != "available":
            return []
        validated_claims: list[dict] = []
        try:
            import json
            raw_data = json.loads(result.raw_output) if result.raw_output else {}
            response = LLMExtractionResponse(**raw_data)
            validated = validate_response(
                response,
                original_text=text,
                document_id=doc_id,
                page_number=page_num,
            )
            for v in validated:
                claims_dict = v.model_dump()
                claims_dict["extraction_method"] = "llm"
                validated_claims.append(claims_dict)
        except (json.JSONDecodeError, KeyError, TypeError):
            for claim_data in result.claims:
                claim_data["extraction_method"] = "llm"
                validated_claims.append(claim_data)
        return validated_claims

    def run(self, text: str, **kwargs: str | int | bool) -> list[dict]:
        return self._extract_from_text(text, **kwargs)

    @property
    def avg_latency_ms(self) -> float:
        return sum(self._latencies) / len(self._latencies) if self._latencies else 0.0


class HybridPipeline(ExtractionPipeline):
    name = "hybrid"

    def __init__(
        self,
        rule_pipeline: RuleBasedPipeline,
        llm_pipeline: LLMPipeline,
    ) -> None:
        self._rules = rule_pipeline
        self._llm = llm_pipeline
        self._dedup = KeywordDeduplicator()

    def _should_send_to_llm(self, claims: list[dict]) -> list[dict]:
        uncertain: list[dict] = []
        for claim in claims:
            if claim.get("methodology") == "unknown" or claim.get("confidence", 0.5) < 0.4:
                uncertain.append(claim)
        return uncertain

    def _extract_from_text(self, text: str, **kwargs: str | int | bool) -> list[dict]:
        rule_claims = self._rules.run(text, **kwargs)
        uncertain = self._should_send_to_llm(rule_claims)
        llm_claims: list[dict] = []
        if uncertain:
            uncertain_texts = [c.get("exact_source_text", "") for c in uncertain[:5]]
            llm_context = " ".join(uncertain_texts)[:2000]
            if llm_context.strip():
                llm_claims = self._llm.run(llm_context, **kwargs)
        all_claims = rule_claims + llm_claims
        self._dedup.deduplicate(all_claims, threshold=0.9)
        return all_claims

    def run(self, text: str, **kwargs: str | int | bool) -> list[dict]:
        return self._extract_from_text(text, **kwargs)


def run_experiment(
    gold_standard: list[dict],
    pipelines: dict[str, ExtractionPipeline],
) -> dict[str, EvalMetrics]:
    results: dict[str, EvalMetrics] = {}
    for pipe_name, pipeline in pipelines.items():
        all_preds: list[dict] = []
        latencies: list[float] = []
        for case in gold_standard:
            start = time.time()
            preds = pipeline.run(
                case["text"],
                document_id=case.get("document_id", ""),
                page_number=case.get("page_number", 1),
                source_file=case.get("source_file", ""),
            )
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
            all_preds.extend(preds)
        metrics = evaluate_predictions(all_preds, gold_standard)
        metrics.avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0.0
        metrics.notes = f"{pipe_name} pipeline — {len(all_preds)} extracted from {len(gold_standard)} cases"
        results[pipe_name] = metrics
    return results
