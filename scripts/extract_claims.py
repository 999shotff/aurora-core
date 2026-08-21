"""Phase 4 — Deterministic claim extraction pipeline.

Processes the 40-PDF research corpus.
Produces machine-readable artifacts.
No LLM involvement.
"""
from __future__ import annotations

import json
from pathlib import Path

from aurora.research.claims import ClaimExtractionResult, ResearchClaim
from aurora.research.conflict_detector import detect_conflicts
from aurora.research.duplicate_detector import deduplicate_claims, detect_duplicates
from aurora.research.extractor import extract_claims_from_page
from aurora.research.feature_mapper import map_claims_to_features
from aurora.research.formula_extractor import extract_formulas
from aurora.research.graph_builder import build_knowledge_graph
from aurora.research.hypothesis_extractor import extract_hypotheses
from aurora.research.models import ResearchPage
from aurora.research.storage import ResearchStorage


def load_pages(extracted_dir: Path, doc_entry: dict) -> list[ResearchPage]:
    pages: list[ResearchPage] = []
    pages_dir = extracted_dir / "pages"
    doc_id = doc_entry["document_id"]
    page_count = doc_entry.get("page_count", 0)

    for page_num in range(1, page_count + 1):
        page_id = f"{doc_id}_p{page_num}"
        page_path = pages_dir / f"{page_id}.json"
        if not page_path.exists():
            continue
        data = json.loads(page_path.read_text(encoding="utf-8"))
        pages.append(ResearchPage(
            page_id=page_id,
            document_id=doc_id,
            page_number=page_num,
            text=data.get("text", ""),
            char_count=len(data.get("text", "")),
            extraction_quality=data.get("extraction_quality", "unknown"),
        ))
    return pages


def run_extraction() -> None:
    extracted_dir = Path("/sdcard/Download/aurora-core/research/extracted")
    output_dir = Path("/sdcard/Download/aurora-core/research/extracted")
    index_path = extracted_dir / "index" / "research_index.json"

    if not index_path.exists():
        print(f"ERROR: index not found at {index_path}")
        return

    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    documents = index_data.get("documents", [])

    print(f"Loaded index: {len(documents)} documents")

    storage = ResearchStorage(output_dir)
    storage.ensure_dirs()

    all_claims: list[ResearchClaim] = []
    all_results: list[ClaimExtractionResult] = []

    for doc_entry in documents:
        doc_id = doc_entry["document_id"]
        filename = doc_entry.get("source_filename", doc_entry.get("title", doc_id))
        source_sha = doc_entry.get("sha256", "")
        page_count = doc_entry.get("page_count", 0)

        print(f"\n  Processing: {filename} (id={doc_id})")

        pages = load_pages(extracted_dir, doc_entry)
        if not pages:
            print("    No pages loaded, skipping")
            continue

        page_claims: list[ResearchClaim] = []
        for page in pages:
            pc = extract_claims_from_page(
                page=page,
                document_id=doc_id,
                source_file=filename,
                source_sha256=source_sha,
            )
            page_claims.extend(pc)

        claims_by_type: dict[str, int] = {}
        claims_by_methodology: dict[str, int] = {}
        for c in page_claims:
            claims_by_type[c.claim_type] = claims_by_type.get(c.claim_type, 0) + 1
            claims_by_methodology[c.methodology] = claims_by_methodology.get(c.methodology, 0) + 1

        result = ClaimExtractionResult(
            document_id=doc_id,
            source_file=filename,
            source_sha256=source_sha,
            total_pages=page_count,
            pages_processed=len(pages),
            claims_extracted=len(page_claims),
            hypotheses_extracted=0,
            formulas_extracted=0,
            ocr_derived_claims=0,
            extraction_failures=0,
            claims_by_type=claims_by_type,
            claims_by_methodology=claims_by_methodology,
        )

        all_claims.extend(page_claims)
        all_results.append(result)

        print(f"    pages={len(pages)}/{page_count}, claims={len(page_claims)}")

    print(f"\n{'=' * 60}")
    print("EXTRACTION SUMMARY")
    print(f"{'=' * 60}")

    total_claims = len(all_claims)

    all_type_dist: dict[str, int] = {}
    all_meth_dist: dict[str, int] = {}
    for r in all_results:
        for k, v in r.claims_by_type.items():
            all_type_dist[k] = all_type_dist.get(k, 0) + v
        for k, v in r.claims_by_methodology.items():
            all_meth_dist[k] = all_meth_dist.get(k, 0) + v

    print(f"Documents processed:    {len(all_results)}")
    print(f"Total claims extracted: {total_claims}")

    print("\nClaims by type:")
    for k, v in sorted(all_type_dist.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    print("\nClaims by methodology:")
    for k, v in sorted(all_meth_dist.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    print("\nExtracting hypotheses...")
    hypotheses = extract_hypotheses(all_claims)
    print(f"  Hypotheses: {len(hypotheses)}")

    print("\nExtracting formulas...")
    formulas = extract_formulas(all_claims)
    print(f"  Formulas: {len(formulas)}")

    print("\nDetecting conflicts...")
    conflicts = detect_conflicts(all_claims)
    print(f"  Conflicts: {len(conflicts)}")

    print("\nDetecting duplicates...")
    duplicates = detect_duplicates(all_claims)
    print(f"  Duplicate candidates: {len(duplicates)}")

    print("\nMapping claims to features...")
    feature_mappings = map_claims_to_features(all_claims)
    print(f"  Feature mappings: {len(feature_mappings)}")

    print("\nDeduplicating claims...")
    deduped_claims = deduplicate_claims(all_claims, duplicates)
    print(f"  Claims after dedup: {len(deduped_claims)}")

    print("\nBuilding knowledge graph...")
    doc_dicts = [
        {"document_id": r.document_id, "filename": r.source_file.split("/")[-1]}
        for r in all_results
    ]
    graph = build_knowledge_graph(
        documents=doc_dicts,
        claims=deduped_claims,
        hypotheses=hypotheses,
        formulas=formulas,
        feature_mappings=feature_mappings,
        conflicts=conflicts,
    )
    print(f"  Nodes: {len(graph.nodes)}")
    print(f"  Edges: {len(graph.edges)}")

    print("\nSaving artifacts...")
    for claim in deduped_claims:
        storage.save_claim(claim)
    for hyp in hypotheses:
        storage.save_hypothesis(hyp)
    for formula in formulas:
        storage.save_formula(formula)
    storage.save_graph(graph)

    summary = {
        "documents_processed": len(all_results),
        "total_claims": len(deduped_claims),
        "total_hypotheses": len(hypotheses),
        "total_formulas": len(formulas),
        "total_conflicts": len(conflicts),
        "total_duplicates": len(duplicates),
        "total_feature_mappings": len(feature_mappings),
        "claims_by_type": all_type_dist,
        "claims_by_methodology": all_meth_dist,
        "graph_nodes": len(graph.nodes),
        "graph_edges": len(graph.edges),
    }
    summary_path = output_dir / "extraction_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"  Summary saved to {summary_path}")

    print(f"\n{'=' * 60}")
    print("EXTRACTION COMPLETE")
    print(f"{'=' * 60}")
    print(f"All artifacts saved to: {output_dir}")


if __name__ == "__main__":
    run_extraction()
