from pathlib import Path

from aurora.research.ingestion import ResearchIngestor
from aurora.research.storage import ResearchStorage


def test_ingestion_no_files(tmp_path: Path):
    root = tmp_path / "empty_research"
    root.mkdir()
    ingestor = ResearchIngestor(root)
    index = ingestor.ingest_all()
    assert index.document_count == 0


def test_ingestion_txt_file(tmp_path: Path):
    root = tmp_path / "research"
    root.mkdir()
    (root / "test.txt").write_text("This is a test document.\n")
    ingestor = ResearchIngestor(root)
    index = ingestor.ingest_all()
    assert index.document_count == 1
    doc = index.documents[0]
    assert doc.extraction_status == "success"
    assert doc.page_count == 1


def test_ingestion_markdown_file(tmp_path: Path):
    root = tmp_path / "research"
    root.mkdir()
    (root / "test.md").write_text("# Chapter 1\n\nSome content.\n")
    ingestor = ResearchIngestor(root)
    index = ingestor.ingest_all()
    assert index.document_count == 1
    assert index.documents[0].extraction_status == "success"


def test_ingestion_json_file(tmp_path: Path):
    root = tmp_path / "research"
    root.mkdir()
    (root / "test.json").write_text('{"key": "value"}')
    ingestor = ResearchIngestor(root)
    index = ingestor.ingest_all()
    assert index.document_count == 1


def test_ingestion_write_index(tmp_path: Path):
    root = tmp_path / "research"
    root.mkdir()
    (root / "test.txt").write_text("content")
    ingestor = ResearchIngestor(root)
    index = ingestor.ingest_all()
    out = tmp_path / "index.json"
    ingestor.write_index(index, out)
    assert out.exists()


def test_ingestion_sha256_deterministic(tmp_path: Path):
    root = tmp_path / "research"
    root.mkdir()
    (root / "a.txt").write_text("same content")
    ingestor = ResearchIngestor(root)
    idx1 = ingestor.ingest_all()
    idx2 = ingestor.ingest_all()
    assert idx1.documents[0].sha256 == idx2.documents[0].sha256


def test_ingestion_with_storage(tmp_path: Path):
    root = tmp_path / "research"
    root.mkdir()
    (root / "doc.txt").write_text("Research document content.\n")
    ingestor = ResearchIngestor(root)
    index = ingestor.ingest_all()
    storage = ResearchStorage(tmp_path / "kb")
    for doc_record in index.documents:
        from aurora.research.models import ResearchDocument, ResearchSource

        doc = ResearchDocument(
            document_id=doc_record.document_id,
            title=doc_record.filename,
            source=ResearchSource(
                source_path=doc_record.source_path,
                sha256=doc_record.sha256,
                source_type=doc_record.source_type,  # type: ignore[arg-type]
                size_bytes=doc_record.size_bytes,
                filename=doc_record.filename,
            ),
            page_count=doc_record.page_count,
        )
        storage.save_document(doc)
    loaded = storage.load_document(index.documents[0].document_id)
    assert loaded is not None
    assert loaded.title == "doc.txt"
