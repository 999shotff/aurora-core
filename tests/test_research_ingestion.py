from pathlib import Path

from aurora.research.extractors import extract_json, extract_markdown, extract_txt
from aurora.research.ingestion import ResearchIngestor
from aurora.research.schema import ResearchDocumentRecord, ResearchIndex


def test_extract_txt(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("Hello world\nSecond line", encoding="utf-8")
    structure, errors = extract_txt(p)
    assert len(structure.pages) == 1
    assert structure.pages[0].text == "Hello world\nSecond line"
    assert structure.pages[0].page_number == 1
    assert len(errors) == 0


def test_extract_markdown(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("# Title\n\nSome text\n\n## Section\n\nMore text", encoding="utf-8")
    structure, errors = extract_markdown(p)
    assert len(structure.pages) == 1
    assert len(structure.sections) == 2
    assert structure.sections[0].heading == "Title"
    assert structure.sections[1].heading == "Section"
    assert len(errors) == 0


def test_extract_json(tmp_path: Path):
    p = tmp_path / "test.json"
    p.write_text('{"key": "value"}', encoding="utf-8")
    structure, errors = extract_json(p)
    assert len(structure.pages) == 1
    assert len(errors) == 0


def test_extract_json_invalid(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid json", encoding="utf-8")
    _structure, errors = extract_json(p)
    assert any(e.error_type == "json_parse_error" for e in errors)


def test_extract_txt_utf8_error(tmp_path: Path):
    p = tmp_path / "bad.txt"
    p.write_bytes(b"\xff\xfe")
    _structure, errors = extract_txt(p)
    assert any(e.error_type == "decode_error" for e in errors)


def test_sha256_stability(tmp_path: Path):
    p = tmp_path / "doc.txt"
    p.write_text("content", encoding="utf-8")
    sha1 = ResearchIngestor._sha256(p)
    sha2 = ResearchIngestor._sha256(p)
    assert sha1 == sha2
    assert len(sha1) == 64


def test_ingest_file_txt(tmp_path: Path):
    p = tmp_path / "research" / "doc.txt"
    p.parent.mkdir(parents=True)
    p.write_text("Research content here", encoding="utf-8")

    ingestor = ResearchIngestor(tmp_path / "research", tmp_path / "extracted")
    record = ingestor.ingest_file(p)

    assert isinstance(record, ResearchDocumentRecord)
    assert record.extraction_status == "success"
    assert record.page_count == 1
    assert record.source_type == "txt"
    assert len(record.sha256) == 64
    assert Path(record.text_location).exists()


def test_ingest_file_markdown(tmp_path: Path):
    p = tmp_path / "research" / "doc.md"
    p.parent.mkdir(parents=True)
    p.write_text("# Title\n\nContent", encoding="utf-8")

    ingestor = ResearchIngestor(tmp_path / "research", tmp_path / "extracted")
    record = ingestor.ingest_file(p)

    assert record.extraction_status == "success"
    assert record.source_type == "md"
    assert len(record.structure.sections) == 1


def test_ingest_all(tmp_path: Path):
    research = tmp_path / "research"
    research.mkdir()
    (research / "a.txt").write_text("aaa", encoding="utf-8")
    (research / "b.md").write_text("# B", encoding="utf-8")
    (research / "c.json").write_text('{"c": 1}', encoding="utf-8")

    ingestor = ResearchIngestor(research, tmp_path / "extracted")
    index = ingestor.ingest_all()

    assert isinstance(index, ResearchIndex)
    assert index.document_count == 3
    assert len(index.documents) == 3


def test_index_round_trip(tmp_path: Path):
    research = tmp_path / "research"
    research.mkdir()
    (research / "doc.txt").write_text("content", encoding="utf-8")

    ingestor = ResearchIngestor(research, tmp_path / "extracted")
    index = ingestor.ingest_all()

    index_path = tmp_path / "index" / "documents.json"
    ingestor.write_index(index, index_path)
    assert index_path.exists()

    loaded = ingestor.load_index(index_path)
    assert loaded.document_count == index.document_count
    assert loaded.documents[0].sha256 == index.documents[0].sha256


def test_document_id_stable(tmp_path: Path):
    p = tmp_path / "research" / "doc.txt"
    p.parent.mkdir(parents=True)
    p.write_text("content", encoding="utf-8")

    ingestor = ResearchIngestor(tmp_path / "research", tmp_path / "extracted")
    r1 = ingestor.ingest_file(p)
    r2 = ingestor.ingest_file(p)
    assert r1.document_id == r2.document_id
