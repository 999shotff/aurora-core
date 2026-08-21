from pathlib import Path

from aurora.research import ResearchIndexer


def test_research_indexer(tmp_path: Path):
    research = tmp_path / "research"
    research.mkdir()
    (research / "book.txt").write_text("research", encoding="utf-8")
    docs = ResearchIndexer(research).scan()
    assert len(docs) == 1
    assert docs[0].filename == "book.txt"
    assert len(docs[0].sha256) == 64
