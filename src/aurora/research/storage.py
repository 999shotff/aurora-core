from __future__ import annotations

import json
from pathlib import Path

from aurora.research.claims import ResearchClaim
from aurora.research.formulas import ResearchFormula
from aurora.research.graph import ResearchKnowledgeGraph
from aurora.research.hypotheses import ResearchHypothesis
from aurora.research.models import ResearchDocument


class ResearchStorage:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self._dirs = {
            "documents": self.base_dir / "documents",
            "pages": self.base_dir / "pages",
            "sections": self.base_dir / "sections",
            "claims": self.base_dir / "claims",
            "hypotheses": self.base_dir / "hypotheses",
            "formulas": self.base_dir / "formulas",
            "graph": self.base_dir / "graph",
            "index": self.base_dir / "index",
        }

    def ensure_dirs(self) -> None:
        for d in self._dirs.values():
            d.mkdir(parents=True, exist_ok=True)

    def _write_json(self, path: Path, data: dict | list) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return path

    def _read_json(self, path: Path) -> dict | list:
        if not path.exists():
            return {} if path.suffix == ".json" else []
        return json.loads(path.read_text(encoding="utf-8"))

    def save_document(self, doc: ResearchDocument) -> Path:
        path = self._dirs["documents"] / f"{doc.document_id}.json"
        return self._write_json(path, doc.model_dump(mode="json"))

    def load_document(self, document_id: str) -> ResearchDocument | None:
        path = self._dirs["documents"] / f"{document_id}.json"
        if not path.exists():
            return None
        data = self._read_json(path)
        return ResearchDocument.model_validate(data)

    def save_claim(self, claim: ResearchClaim) -> Path:
        path = self._dirs["claims"] / f"{claim.claim_id}.json"
        return self._write_json(path, claim.model_dump(mode="json"))

    def load_claim(self, claim_id: str) -> ResearchClaim | None:
        path = self._dirs["claims"] / f"{claim_id}.json"
        if not path.exists():
            return None
        data = self._read_json(path)
        return ResearchClaim.model_validate(data)

    def list_claims(self) -> list[str]:
        claims_dir = self._dirs["claims"]
        if not claims_dir.exists():
            return []
        return sorted(p.stem for p in claims_dir.glob("*.json"))

    def save_hypothesis(self, hyp: ResearchHypothesis) -> Path:
        path = self._dirs["hypotheses"] / f"{hyp.hypothesis_id}.json"
        return self._write_json(path, hyp.model_dump(mode="json"))

    def load_hypothesis(self, hypothesis_id: str) -> ResearchHypothesis | None:
        path = self._dirs["hypotheses"] / f"{hypothesis_id}.json"
        if not path.exists():
            return None
        data = self._read_json(path)
        return ResearchHypothesis.model_validate(data)

    def list_hypotheses(self) -> list[str]:
        hyp_dir = self._dirs["hypotheses"]
        if not hyp_dir.exists():
            return []
        return sorted(p.stem for p in hyp_dir.glob("*.json"))

    def save_formula(self, formula: ResearchFormula) -> Path:
        path = self._dirs["formulas"] / f"{formula.formula_id}.json"
        return self._write_json(path, formula.model_dump(mode="json"))

    def load_formula(self, formula_id: str) -> ResearchFormula | None:
        path = self._dirs["formulas"] / f"{formula_id}.json"
        if not path.exists():
            return None
        data = self._read_json(path)
        return ResearchFormula.model_validate(data)

    def list_formulas(self) -> list[str]:
        f_dir = self._dirs["formulas"]
        if not f_dir.exists():
            return []
        return sorted(p.stem for p in f_dir.glob("*.json"))

    def save_graph(self, graph: ResearchKnowledgeGraph) -> Path:
        path = self._dirs["graph"] / "knowledge_graph.json"
        return self._write_json(path, graph.model_dump(mode="json"))

    def load_graph(self) -> ResearchKnowledgeGraph:
        path = self._dirs["graph"] / "knowledge_graph.json"
        if not path.exists():
            return ResearchKnowledgeGraph()
        data = self._read_json(path)
        return ResearchKnowledgeGraph.model_validate(data)

    def save_index(self, index: dict) -> Path:
        path = self._dirs["index"] / "research_index.json"
        return self._write_json(path, index)

    def load_index(self) -> dict:
        path = self._dirs["index"] / "research_index.json"
        data = self._read_json(path)
        return data if isinstance(data, dict) else {}
