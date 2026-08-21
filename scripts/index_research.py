from pathlib import Path

from aurora.research import ResearchIndexer


def main() -> None:
    root = Path("research")
    output = Path("research/index/documents.json")
    indexer = ResearchIndexer(root)
    result = indexer.write_index(output)
    print(f"Wrote research index: {result}")
    print(f"Documents: {len(indexer.scan())}")

if __name__ == "__main__":
    main()
