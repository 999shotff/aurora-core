"""Research Knowledge Graph builder for Phase 4.

Populates the graph with DOCUMENT → PAGE → CLAIM → HYPOTHESIS → FEATURE → FORMULA
and their relationships.
"""
from __future__ import annotations

from aurora.research.claims import ResearchClaim
from aurora.research.feature_mapper import ClaimFeatureMapping
from aurora.research.formulas import ResearchFormula
from aurora.research.graph import GraphEdge, GraphNode, ResearchKnowledgeGraph
from aurora.research.hypotheses import ResearchHypothesis


def build_knowledge_graph(
    documents: list[dict[str, str | int]],
    claims: list[ResearchClaim],
    hypotheses: list[ResearchHypothesis],
    formulas: list[ResearchFormula],
    feature_mappings: list[ClaimFeatureMapping],
    conflicts: list[GraphEdge],
) -> ResearchKnowledgeGraph:
    graph = ResearchKnowledgeGraph()

    for doc in documents:
        graph.add_node(GraphNode(
            node_id=f"doc_{doc['document_id']}",
            node_type="document",
            label=str(doc.get("filename", doc["document_id"])),
        ))

    seen_pages: set[str] = set()
    for claim in claims:
        page_node_id = f"page_{claim.document_id}_p{claim.page}"
        if page_node_id not in seen_pages:
            seen_pages.add(page_node_id)
            graph.add_node(GraphNode(
                node_id=page_node_id,
                node_type="page",
                label=f"Page {claim.page}",
            ))
            graph.add_edge(GraphEdge(
                source_id=f"doc_{claim.document_id}",
                target_id=page_node_id,
                relationship="contains",
            ))

        claim_node_id = f"claim_{claim.claim_id}"
        graph.add_node(GraphNode(
            node_id=claim_node_id,
            node_type="claim",
            label=claim.normalized_text[:80],
        ))
        graph.add_edge(GraphEdge(
            source_id=page_node_id,
            target_id=claim_node_id,
            relationship="extracted_from",
        ))

    for hyp in hypotheses:
        hyp_node_id = f"hyp_{hyp.hypothesis_id}"
        graph.add_node(GraphNode(
            node_id=hyp_node_id,
            node_type="hypothesis",
            label=f"{hyp.condition} → {hyp.expected_effect}"[:80],
        ))
        claim_node_id = f"claim_{hyp.source_claim_id}"
        if claim_node_id in graph.nodes:
            graph.add_edge(GraphEdge(
                source_id=claim_node_id,
                target_id=hyp_node_id,
                relationship="tested_by",
            ))

    for formula in formulas:
        formula_node_id = f"formula_{formula.formula_id}"
        graph.add_node(GraphNode(
            node_id=formula_node_id,
            node_type="formula",
            label=formula.expression[:80],
        ))
        claim_node_id = f"claim_{formula.source_claim_id}"
        if claim_node_id in graph.nodes:
            graph.add_edge(GraphEdge(
                source_id=claim_node_id,
                target_id=formula_node_id,
                relationship="derived_from",
            ))

    seen_features: set[str] = set()
    for mapping in feature_mappings:
        feature_node_id = f"feature_{mapping.feature_name}"
        if feature_node_id not in seen_features:
            seen_features.add(feature_node_id)
            graph.add_node(GraphNode(
                node_id=feature_node_id,
                node_type="feature",
                label=mapping.feature_name,
            ))
        claim_node_id = f"claim_{mapping.claim_id}"
        if claim_node_id in graph.nodes:
            graph.add_edge(GraphEdge(
                source_id=claim_node_id,
                target_id=feature_node_id,
                relationship="depends_on",
            ))

    for conflict in conflicts:
        if conflict.source_id in graph.nodes and conflict.target_id in graph.nodes:
            graph.add_edge(conflict)

    return graph
