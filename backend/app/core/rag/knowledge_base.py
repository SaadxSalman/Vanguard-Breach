"""Adversarial knowledge base — the tactical brain of Vanguard-Breach.

Collections:
  threats   – OWASP LLM Top-10, MITRE ATLAS techniques, CVE/research intel
  mutations – linguistic obfuscations & token-smuggling patterns
  poisoning – knowledge-base poisoning playbooks
  user_docs – documents ingested by the operator (also used by the
              Semantic Poisoning Engine for controlled poisoning drills)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ... import db
from ...config import get_settings
from .embeddings import get_encoder
from .vector_store import get_vector_store

SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"
COLLECTIONS = ("threats", "mutations", "poisoning", "user_docs")

_SEED_FILES = {
    "threats": ["owasp_llm_top10.json", "mitre_atlas.json",
                "injection_patterns.json", "evasion_patterns.json"],
    "mutations": ["mutation_patterns.json"],
    "poisoning": ["poisoning_patterns.json"],
}


class AdversarialKnowledgeBase:
    def __init__(self) -> None:
        self.store = get_vector_store()
        self.encoder = get_encoder()

    # ── bootstrap ────────────────────────────────────────────────────────────
    def bootstrap(self, force: bool = False) -> dict[str, int]:
        """Seed the vector store from bundled threat intel (idempotent)."""
        seeded = {"inserted": 0, "skipped": 0}
        existing = {v["id"] for v in db.query("SELECT id FROM kb_docs WHERE source='seed'")}
        for collection, files in _SEED_FILES.items():
            batch: list[dict[str, Any]] = []
            for filename in files:
                path = SEED_DIR / filename
                if not path.exists():
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
                for entry in payload:
                    doc_id = f"seed:{entry['id']}"
                    if doc_id in existing and not force:
                        seeded["skipped"] += 1
                        continue
                    text = self._as_text(entry)
                    batch.append({
                        "id": doc_id,
                        "vector": self.encoder.encode(text),
                        "payload": {
                            "doc_id": doc_id, "collection_kind": collection,
                            "category": entry.get("category", "threat"),
                            "title": entry.get("title") or entry.get("name", entry["id"]),
                            "owasp": entry.get("owasp", ""), "atlas": entry.get("atlas", ""),
                            "severity_hint": entry.get("severity_hint", 5.0),
                            "text": text[:2000],
                        }})
                    if doc_id not in existing:
                        db.insert("kb_docs", {
                            "id": doc_id, "source": "seed",
                            "category": entry.get("category", "threat"),
                            "title": entry.get("title") or entry.get("name", entry["id"]),
                            "content": text, "meta": db.dumps(entry), "created_at": db.now()})
            if batch:
                self.store.upsert(collection, batch)
                seeded["inserted"] += len(batch)
        return seeded

    @staticmethod
    def _as_text(entry: dict[str, Any]) -> str:
        parts = [entry.get("id", ""), entry.get("title") or entry.get("name", ""),
                 entry.get("description", ""), entry.get("objective", ""),
                 entry.get("pattern", entry.get("template", "")),
                 " ".join(entry.get("tags", []))]
        return " \n".join(str(p) for p in parts if p)

    # ── query / ingest ───────────────────────────────────────────────────────
    def search(self, query: str, collection: str = "threats", limit: int = 5,
               flt: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        vector = self.encoder.encode(query)
        return self.store.search(collection, vector, limit=limit, flt=flt)

    def contextual_search(self, domain: str, objective: str, limit: int = 5) -> list[dict[str, Any]]:
        """Match target domain context to bypass vectors & threat techniques."""
        query = f"{domain} application security testing {objective}"
        threats = self.search(query, "threats", limit=limit)
        mutations = self.search(query, "mutations", limit=max(2, limit // 2))
        return threats + mutations

    def ingest(self, title: str, content: str, category: str = "custom",
               source: str = "manual", meta: dict[str, Any] | None = None,
               collection: str = "user_docs") -> dict[str, Any]:
        doc_id = db.new_id("doc")
        db.insert("kb_docs", {"id": doc_id, "source": source, "category": category,
                              "title": title, "content": content,
                              "meta": db.dumps(meta or {}), "created_at": db.now()})
        self.store.upsert(collection, [{
            "id": doc_id, "vector": self.encoder.encode(f"{title} {content}"),
            "payload": {"doc_id": doc_id, "collection_kind": collection, "category": category,
                        "title": title, "source": source, "text": content[:2000], **(meta or {})}}])
        return {"id": doc_id, "title": title, "category": category}

    def list_docs(self, source: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        if source:
            rows = db.query("SELECT * FROM kb_docs WHERE source=? ORDER BY created_at DESC LIMIT ?",
                            (source, limit))
        else:
            rows = db.query("SELECT * FROM kb_docs ORDER BY created_at DESC LIMIT ?", (limit,))
        for row in rows:
            row["meta"] = db.loads(row["meta"], {})
        return rows

    def delete_doc(self, doc_id: str) -> bool:
        row = db.query_one("SELECT * FROM kb_docs WHERE id=?", (doc_id,))
        if not row:
            return False
        db.execute("DELETE FROM kb_docs WHERE id=?", (doc_id,))
        for collection in COLLECTIONS:
            self.store.delete(collection, lambda p, d=doc_id: p.get("doc_id") == d)
        return True

    def stats(self) -> dict[str, Any]:
        rows = db.query("SELECT source, category, COUNT(*) AS n FROM kb_docs GROUP BY source, category")
        by_source: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for row in rows:
            by_source[row["source"]] = by_source.get(row["source"], 0) + row["n"]
            by_category[row["category"]] = by_category.get(row["category"], 0) + row["n"]
        return {"total_docs": sum(by_source.values()), "by_source": by_source,
                "by_category": by_category, "store": self.store.status(),
                "embedding_provider": self.encoder.name}


_KB: AdversarialKnowledgeBase | None = None


def get_kb() -> AdversarialKnowledgeBase:
    global _KB
    if _KB is None:
        _KB = AdversarialKnowledgeBase()
    return _KB
