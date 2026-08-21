import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResearchDocument:
    document_id: str
    filename: str
    path: str
    suffix: str
    size_bytes: int
    sha256: str


class ResearchIndexer:
    SUPPORTED: frozenset[str] = frozenset({".pdf", ".txt", ".md", ".json"})

    def __init__(self, root: str | Path):
        self.root = Path(root)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def scan(self) -> list[ResearchDocument]:
        if not self.root.exists():
            return []
        documents = []
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in self.SUPPORTED:
                continue
            sha = self._sha256(path)
            documents.append(
                ResearchDocument(
                    document_id=sha[:16],
                    filename=path.name,
                    path=str(path),
                    suffix=path.suffix.lower(),
                    size_bytes=path.stat().st_size,
                    sha256=sha,
                )
            )
        return documents

    def write_index(self, output: str | Path) -> Path:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(doc) for doc in self.scan()]
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return destination
