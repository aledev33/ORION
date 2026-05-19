import json
from pathlib import Path


class LocalProvider:
    name = "local"

    def __init__(self, kb_path: str | None = None):
        self.kb_path = Path(kb_path) if kb_path else Path(__file__).resolve().parents[1] / "local_kb.json"
        self.kb = {}
        if self.kb_path.exists():
            self.kb = json.loads(self.kb_path.read_text(encoding="utf-8"))

    def available(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 3) -> dict:
        q = query.lower().strip()
        # match simple por substring / clave exacta
        for k, v in self.kb.items():
            if k in q or q in k:
                return {"hit": k, "text": v}
        return {}

    def to_text(self, data: dict) -> str:
        return (data.get("text") or "").strip()