"""Quick OCR verification — 3 pages per zero-text document."""
from __future__ import annotations

import json
from pathlib import Path

from aurora.research.ocr import get_ocr_provider
from aurora.research.page_quality import ocr_page

ZERO_TEXT_DOCS = [
    "The Law of Vibration- The Revelation of William D. Gann -- Tony Plummer -- ( WeLib.org ).pdf",
    "fibonacci-lucas (1).pdf",
    "varahmihirHorasastram (1).pdf",
]


def quick_ocr_test():
    pdfs_dir = Path("/sdcard/Download/aurora-core/research/pdfs")
    extracted_dir = Path("/sdcard/Download/aurora-core/research/extracted")
    pages_dir = extracted_dir / "pages"

    provider = get_ocr_provider()
    if not provider.is_available():
        print("OCR UNAVAILABLE")
        print("Required: tesseract-ocr, pytesseract, Pillow, pdf2image")
        return

    print(f"OCR engine: {provider.engine_name()} {provider.engine_version()}")
    print()

    test_pages = [1, 50, 100]
    results = []

    for pdf_name in ZERO_TEXT_DOCS:
        pdf_path = pdfs_dir / pdf_name
        if not pdf_path.exists():
            print(f"SKIP: {pdf_name}")
            continue

        # Find doc_id
        doc_json = None
        for f in (extracted_dir / "documents").glob("*.json"):
            data = json.loads(f.read_text())
            if data.get("source", {}).get("filename") == pdf_name:
                doc_json = data
                break

        if not doc_json:
            print(f"ERROR: no record for {pdf_name}")
            continue

        doc_id = doc_json["document_id"]
        page_count = doc_json["page_count"]
        print(f"Document: {pdf_name}")
        print(f"  doc_id={doc_id}, pages={page_count}")

        for page_num in test_pages:
            if page_num > page_count:
                continue

            page_id = f"{doc_id}_p{page_num}"
            page_path = pages_dir / f"{page_id}.json"
            original_text = ""
            if page_path.exists():
                original_text = json.loads(page_path.read_text()).get("text", "")

            result = ocr_page(
                pdf_path=pdf_path,
                page_number=page_num,
                document_id=doc_id,
                original_text=original_text,
                original_quality="ocr_required",
                provider=provider,
                output_dir=extracted_dir,
            )

            if result.ocr_result and result.ocr_result.ocr_status == "success":
                text_preview = result.ocr_result.ocr_text[:200].replace("\n", " ")
                print(f"  page {page_num}: OK, {result.ocr_result.char_count} chars, "
                      f"conf={result.ocr_result.confidence:.1f}%, "
                      f"preview: {text_preview[:80]}...")
                results.append({
                    "doc": pdf_name,
                    "page": page_num,
                    "chars": result.ocr_result.char_count,
                    "confidence": result.ocr_result.confidence,
                })
            else:
                print(f"  page {page_num}: FAILED — {result.action_taken}")

        print()

    if results:
        avg_conf = sum(r["confidence"] for r in results) / len(results)
        total_chars = sum(r["chars"] for r in results)
        print(f"Summary: {len(results)} pages OCR'd, avg conf={avg_conf:.1f}%, total chars={total_chars:,}")


if __name__ == "__main__":
    quick_ocr_test()
