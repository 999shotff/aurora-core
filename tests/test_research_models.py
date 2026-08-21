import hashlib

from aurora.research.models import (
    ResearchDocument,
    ResearchPage,
    ResearchParagraph,
    ResearchSection,
    ResearchSource,
    ResearchTable,
)


def _source(sha: str = "") -> ResearchSource:
    if not sha:
        sha = hashlib.sha256(b"test").hexdigest()
    return ResearchSource(
        source_path="/test/doc.pdf",
        sha256=sha,
        source_type="pdf",
        size_bytes=1024,
        filename="doc.pdf",
    )


def test_research_source():
    src = _source()
    assert src.sha256 == hashlib.sha256(b"test").hexdigest()
    assert src.source_type == "pdf"


def test_research_document_identity():
    doc = ResearchDocument(
        document_id="doc_001",
        title="Test Document",
        source=_source(),
        page_count=5,
    )
    assert doc.document_id == "doc_001"
    assert doc.sha256 == _source().sha256
    assert doc.page_count == 5


def test_research_document_deterministic():
    sha = hashlib.sha256(b"deterministic").hexdigest()
    d1 = ResearchDocument(document_id="d1", source=_source(sha), page_count=1)
    d2 = ResearchDocument(document_id="d1", source=_source(sha), page_count=1)
    assert d1.document_id == d2.document_id
    assert d1.sha256 == d2.sha256


def test_research_page():
    page = ResearchPage(
        page_id="page_001",
        document_id="doc_001",
        page_number=1,
        text="Hello world",
        char_count=11,
    )
    assert page.document_id == "doc_001"
    assert page.extraction_quality == "good"


def test_research_section():
    sec = ResearchSection(
        section_id="sec_001",
        document_id="doc_001",
        page_number=1,
        heading="Chapter 1",
        level=1,
    )
    assert sec.heading == "Chapter 1"
    assert sec.level == 1


def test_research_paragraph():
    para = ResearchParagraph(
        paragraph_id="para_001",
        document_id="doc_001",
        page_number=1,
        text="Some text",
        char_count=9,
        index_in_page=0,
    )
    assert para.char_count == 9


def test_research_table():
    tbl = ResearchTable(
        table_id="tbl_001",
        document_id="doc_001",
        page_number=1,
        rows=[["a", "b"], ["c", "d"]],
        row_count=2,
        column_count=2,
    )
    assert tbl.row_count == 2
    assert tbl.column_count == 2


def test_document_serialization_round_trip():
    doc = ResearchDocument(
        document_id="doc_001",
        title="Test",
        source=_source(),
        page_count=2,
    )
    data = doc.model_dump()
    restored = ResearchDocument.model_validate(data)
    assert restored.document_id == doc.document_id
    assert restored.sha256 == doc.sha256
