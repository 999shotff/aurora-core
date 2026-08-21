"""Phase 4.5 — Deterministic claim extraction with OCR integration.

Processes the 40-PDF research corpus.
Routes OCR text through extraction pipeline.
Produces machine-readable artifacts.
No LLM involvement.
"""
from __future__ import annotations

import json
from pathlib import Path

from aurora.research.claims import ClaimExtractionResult, ResearchClaim
from aurora.research.conflict_detector import detect_conflicts
from aurora.research.duplicate_detector import deduplicate_claims, detect_duplicates
from aurora.research.extractor import (
    extract_claims_from_page,
    load_ocr_results,
    select_text_source,
)
from aurora.research.feature_mapper import map_claims_to_features
from aurora.research.formula_extractor import extract_formulas
from aurora.research.graph_builder import build_knowledge_graph
from aurora.research.hypothesis_extractor import extract_hypotheses
from aurora.research.models import ResearchPage
from aurora.research.storage import ResearchStorage


def load_page_data(extracted_dir: Path, doc_id: str, page_num: int) -> dict | None:
    pages_dir = extracted_dir / "pages"
    page_id = f"{doc_id}_p{page_num}"
    page_path = pages_dir / f"{page_id}.json"
    if not page_path.exists():
        return None
    return json.loads(page_path.read_text(encoding="utf-8"))


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

    total_native_pages = 0
    total_ocr_pages = 0
    total_native_claims = 0
    total_ocr_claims = 0

    for doc_entry in documents:
        doc_id = doc_entry["document_id"]
        filename = doc_entry.get("source_filename", doc_entry.get("title", doc_id))
        source_sha = doc_entry.get("sha256", "")
        page_count = doc_entry.get("page_count", 0)

        print(f"\n  Processing: {filename} (id={doc_id})")

        doc_native_pages = 0
        doc_ocr_pages = 0
        doc_native_claims = 0
        doc_ocr_claims = 0
        page_claims: list[ResearchClaim] = []

        for page_num in range(1, page_count + 1):
            page_data = load_page_data(extracted_dir, doc_id, page_num)
            if page_data is None:
                continue

            native_text = page_data.get("text", "")
            native_quality = page_data.get("extraction_quality", "unknown")

            ocr_data = load_ocr_results(extracted_dir, doc_id, page_num)
            ocr_text = ""
            ocr_quality = "ocr_required"
            ocr_engine = ""
            ocr_conf = 0.0

            if ocr_data:
                ocr_text = ocr_data.get("ocr_text", "")
                ocr_quality = "good" if ocr_data.get("char_count", 0) > 50 else "partial"
                ocr_engine = ocr_data.get("ocr_engine", "")
                ocr_conf = ocr_data.get("confidence", 0.0)

            selected_text, source, _reason = select_text_source(
                native_text, native_quality, ocr_text, ocr_quality,
            )

            is_ocr = source == "ocr"
            if is_ocr:
                doc_ocr_pages += 1
            else:
                doc_native_pages += 1

            page = ResearchPage(
                page_id=f"{doc_id}_p{page_num}",
                document_id=doc_id,
                page_number=page_num,
                text=selected_text,
                char_count=len(selected_text),
                extraction_quality=native_quality,
            )

            claims = extract_claims_from_page(
                page=page,
                document_id=doc_id,
                source_file=filename,
                source_sha256=source_sha,
                extraction_method="rule_based",
                is_ocr=is_ocr,
                ocr_engine=ocr_engine,
                ocr_confidence=ocr_conf,
                native_text_quality=native_quality,
                ocr_text_quality=ocr_quality,
                selected_text_source=source,
            )

            if is_ocr:
                doc_ocr_claims += len(claims)
            else:
                doc_native_claims += len(claims)

            page_claims.extend(claims)

        total_native_pages += doc_native_pages
        total_ocr_pages += doc_ocr_pages
        total_native_claims += doc_native_claims
        total_ocr_claims += doc_ocr_claims

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
            pages_processed=doc_native_pages + doc_ocr_pages,
            native_pages=doc_native_pages,
            ocr_pages=doc_ocr_pages,
            claims_extracted=len(page_claims),
            native_claims=doc_native_claims,
            ocr_claims=doc_ocr_claims,
            hypotheses_extracted=0,
            formulas_extracted=0,
            ocr_derived_claims=doc_ocr_claims,
            extraction_failures=0,
            claims_by_type=claims_by_type,
            claims_by_methodology=claims_by_methodology,
        )

        all_claims.extend(page_claims)
        all_results.append(result)

        print(f"    pages={doc_native_pages + doc_ocr_pages}/{page_count} "
              f"(native={doc_native_pages}, ocr={doc_ocr_pages}), "
              f"claims={len(page_claims)} (native={doc_native_claims}, ocr={doc_ocr_claims})")

    print(f"\n{'=' * 60}")
    print("EXTRACTION SUMMARY (Phase 4.5)")
    print(f"{'=' * 60}")

    total_claims = len(all_claims)

    all_type_dist: dict[str, int] = {}
    all_meth_dist: dict[str, int] = {}
    for r in all_results:
        for k, v in r.claims_by_type.items():
            all_type_dist[k] = all_type_dist.get(k, 0) + v
        for k, v in r.claims_by_methodology.items():
            all_meth_dist[k] = all_meth_dist.get(k, 0) + v

    print(f"Documents processed:     {len(all_results)}")
    print(f"Total pages processed:   {total_native_pages + total_ocr_pages}")
    print(f"  Native pages:          {total_native_pages}")
    print(f"  OCR pages:             {total_ocr_pages}")
    print(f"Total claims extracted:  {total_claims}")
    print(f"  Native claims:         {total_native_claims}")
    print(f"  OCR claims:            {total_ocr_claims}")

    unknown_count = all_meth_dist.get("unknown", 0)
    unknown_pct = unknown_count / total_claims * 100 if total_claims > 0 else 0
    print(f"\nUNKNOWN claims: {unknown_count} ({unknown_pct:.1f}%)")

    print("\nClaims by type:")
    for k, v in sorted(all_type_dist.items(), key=lambda x: -x[1]):
        pct = v / total_claims * 100 if total_claims > 0 else 0
        print(f"  {k}: {v} ({pct:.1f}%)")

    print("\nClaims by methodology:")
    for k, v in sorted(all_meth_dist.items(), key=lambda x: -x[1]):
        pct = v / total_claims * 100 if total_claims > 0 else 0
        print(f"  {k}: {v} ({pct:.1f}%)")

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
        "total_pages": total_native_pages + total_ocr_pages,
        "native_pages": total_native_pages,
        "ocr_pages": total_ocr_pages,
        "total_claims": len(deduped_claims),
        "native_claims": total_native_claims,
        "ocr_claims": total_ocr_claims,
        "total_hypotheses": len(hypotheses),
        "total_formulas": len(formulas),
        "total_conflicts": len(conflicts),
        "total_duplicates": len(duplicates),
        "total_feature_mappings": len(feature_mappings),
        "unknown_claims": all_meth_dist.get("unknown", 0),
        "unknown_pct": all_meth_dist.get("unknown", 0) / len(deduped_claims) * 100 if deduped_claims else 0,
        "claims_by_type": all_type_dist,
        "claims_by_methodology": all_meth_dist,
        "graph_nodes": len(graph.nodes),
        "graph_edges": len(graph.edges),
    }
    summary_path = output_dir / "extraction_summary_v45.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"  Summary saved to {summary_path}")

    print(f"\n{'=' * 60}")
    print("EXTRACTION COMPLETE (Phase 4.5)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    run_extraction()
