"""AURORA Reasoning Core — Task Router.

Routes incoming requests to the appropriate domain handler.
Determines required evidence sources and output schema.
Does NOT let the LLM decide which backend tools to execute.
"""

from __future__ import annotations

from aurora.ai.schemas import (
    EvidenceSource,
    ReasoningDomain,
    ReasoningRequest,
    TaskType,
)


class RoutingDecision:
    """Result of task routing."""

    __slots__ = ("domain", "evidence_sources", "output_schema", "task_type")

    def __init__(
        self,
        domain: ReasoningDomain,
        task_type: TaskType,
        evidence_sources: list[EvidenceSource],
        output_schema: str = "structured",
    ) -> None:
        self.domain = domain
        self.task_type = task_type
        self.evidence_sources = evidence_sources
        self.output_schema = output_schema


_TASK_ROUTING: dict[TaskType, RoutingDecision] = {
    TaskType.ANALYZE_MARKET: RoutingDecision(
        domain=ReasoningDomain.MARKET,
        task_type=TaskType.ANALYZE_MARKET,
        evidence_sources=[
            EvidenceSource.MARKET_DATA,
            EvidenceSource.MARKET_ANALYSIS,
        ],
    ),
    TaskType.EXPLAIN_MARKET: RoutingDecision(
        domain=ReasoningDomain.MARKET,
        task_type=TaskType.EXPLAIN_MARKET,
        evidence_sources=[
            EvidenceSource.MARKET_DATA,
            EvidenceSource.MARKET_ANALYSIS,
        ],
    ),
    TaskType.ANALYZE_GEO: RoutingDecision(
        domain=ReasoningDomain.GEO,
        task_type=TaskType.ANALYZE_GEO,
        evidence_sources=[
            EvidenceSource.GEO_OBSERVATION,
            EvidenceSource.GEO_CHANGE,
            EvidenceSource.GEO_TIMESERIES,
        ],
    ),
    TaskType.EXPLAIN_GEO: RoutingDecision(
        domain=ReasoningDomain.GEO,
        task_type=TaskType.EXPLAIN_GEO,
        evidence_sources=[
            EvidenceSource.GEO_OBSERVATION,
            EvidenceSource.GEO_CHANGE,
            EvidenceSource.GEO_TIMESERIES,
        ],
    ),
    TaskType.SUMMARIZE_RESEARCH: RoutingDecision(
        domain=ReasoningDomain.RESEARCH,
        task_type=TaskType.SUMMARIZE_RESEARCH,
        evidence_sources=[
            EvidenceSource.RESEARCH_CLAIM,
        ],
    ),
    TaskType.COMPARE_EVIDENCE: RoutingDecision(
        domain=ReasoningDomain.GENERAL,
        task_type=TaskType.COMPARE_EVIDENCE,
        evidence_sources=[
            EvidenceSource.MARKET_ANALYSIS,
            EvidenceSource.GEO_OBSERVATION,
            EvidenceSource.RESEARCH_CLAIM,
        ],
    ),
    TaskType.EXPLAIN_EVIDENCE: RoutingDecision(
        domain=ReasoningDomain.GENERAL,
        task_type=TaskType.EXPLAIN_EVIDENCE,
        evidence_sources=[
            EvidenceSource.MARKET_ANALYSIS,
            EvidenceSource.GEO_OBSERVATION,
            EvidenceSource.RESEARCH_CLAIM,
        ],
    ),
    TaskType.GENERAL_RESEARCH: RoutingDecision(
        domain=ReasoningDomain.GENERAL,
        task_type=TaskType.GENERAL_RESEARCH,
        evidence_sources=[
            EvidenceSource.MARKET_ANALYSIS,
            EvidenceSource.GEO_OBSERVATION,
            EvidenceSource.RESEARCH_CLAIM,
        ],
    ),
}


def route_request(request: ReasoningRequest) -> RoutingDecision:
    """Route a request to the appropriate handler.

    Determines domain, required evidence sources, and output schema.
    """
    if request.task_type in _TASK_ROUTING:
        return _TASK_ROUTING[request.task_type]

    domain_mapping: dict[ReasoningDomain, TaskType] = {
        ReasoningDomain.MARKET: TaskType.ANALYZE_MARKET,
        ReasoningDomain.GEO: TaskType.ANALYZE_GEO,
        ReasoningDomain.RESEARCH: TaskType.SUMMARIZE_RESEARCH,
    }
    fallback_task = domain_mapping.get(request.domain, TaskType.GENERAL_RESEARCH)
    return _TASK_ROUTING[fallback_task]


def infer_domain_from_query(query: str) -> ReasoningDomain:
    """Infer the domain from the user query text."""
    q = query.lower()
    market_keywords = ["price", "chart", "candle", "ohlc", "rsi", "macd", "trend", "market", "stock", "crypto", "btc", "eth"]
    geo_keywords = ["satellite", "ndvi", "imagery", "geo", "earth", "observation", "aoi", "scene", "spectral"]
    research_keywords = ["hypothesis", "backtest", "experiment", "claim", "research", "paper", "methodology"]

    market_score = sum(1 for kw in market_keywords if kw in q)
    geo_score = sum(1 for kw in geo_keywords if kw in q)
    research_score = sum(1 for kw in research_keywords if kw in q)

    scores = [
        (ReasoningDomain.MARKET, market_score),
        (ReasoningDomain.GEO, geo_score),
        (ReasoningDomain.RESEARCH, research_score),
    ]
    best = max(scores, key=lambda x: x[1])
    if best[1] > 0:
        return best[0]
    return ReasoningDomain.GENERAL
