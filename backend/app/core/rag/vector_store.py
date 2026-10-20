"""Vector store abstraction: local (SQLite-backed) | Qdrant REST | Milvus REST.

The local store keeps everything in SQLite (persisted) with an in-memory
cache and pure-python cosine search — optional NumPy acceleration if present.
"""
from __future__ import annotations

import json
import math
import threading
from typing import Any, Callable

import httpx

from ... import db
from ...config import get_settings

try:  # optional accelerator
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

Filter = dict[str, Any] | None


def cosine(a: list[float], b: list[float]) -> float:
    if np is not None and len(a) > 64:
        return float(np.dot(a, b))
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def _matches(payload: dict[str, Any], flt: Filter) -> bool:
    if not flt:
        return True
    for key, expected in flt.items():
        if key.startswith("$"):
            continue
        actual = payload.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    for key, regex in (flt.get("$like") or {}).items():
        if regex.lower() not in str(payload.get(key, "")).lower():
            return False
    return True


class LocalVectorStore:
    """SQLite-persisted cosine index with payload filtering."""

    backend = "local"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache: dict[str, list[tuple[str, list[float], dict[str, Any]]]] = {}
        self._loaded: set[str] = set()

    def _ensure(self, collection: str) -> None:
        with self._lock:
            if collection in self._loaded:
                return
            rows = db.query("SELECT id, vector, payload FROM vectors WHERE collection=?", (collection,))
            self._cache[collection] = [
                (r["id"], json.loads(r["vector"]), json.loads(r["payload"])) for r in rows]
            self._loaded.add(collection)

    def upsert(self, collection: str, items: list[dict[str, Any]]) -> None:
        """items: [{id, vector, payload}]"""
        ts = db.now()
        with self._lock:
            for item in items:
                db.execute(
                    "INSERT INTO vectors (collection, id, vector, payload, created_at) VALUES (?,?,?,?,?) "
                    "ON CONFLICT(collection, id) DO UPDATE SET vector=excluded.vector, payload=excluded.payload",
                    (collection, item["id"], json.dumps(item["vector"]),
                     json.dumps(item.get("payload", {})), ts))
            self._cache.pop(collection, None)
            self._loaded.discard(collection)

    def search(self, collection: str, vector: list[float], limit: int = 5,
               flt: Filter = None) -> list[dict[str, Any]]:
        with self._lock:
            self._ensure(collection)
            scored = [(cosine(vector, v), i, p) for i, v, p in self._cache[collection]
                      if _matches(p, flt)]
        scored.sort(key=lambda t: t[0], reverse=True)
        return [{"id": i, "score": round(s, 4), "payload": p} for s, i, p in scored[:limit]]

    def delete(self, collection: str, predicate: Callable[[dict[str, Any]], bool]) -> int:
        with self._lock:
            self._ensure(collection)
            targets = [i for i, _, p in self._cache[collection] if predicate(p)]
            for item_id in targets:
                db.execute("DELETE FROM vectors WHERE collection=? AND id=?", (collection, item_id))
            self._cache.pop(collection, None)
            self._loaded.discard(collection)
        return len(targets)

    def count(self, collection: str) -> int:
        with self._lock:
            self._ensure(collection)
            return len(self._cache[collection])

    def status(self) -> dict[str, Any]:
        return {"backend": "local", "collections": {
            "threats": self.count("threats"), "mutations": self.count("mutations"),
            "poisoning": self.count("poisoning"), "user_docs": self.count("user_docs")}}



class QdrantVectorStore:
    backend = "qdrant"

    def __init__(self) -> None:
        s = get_settings()
        self._url = s.qdrant_url.rstrip("/")
        self._headers = {"api-key": s.qdrant_api_key} if s.qdrant_api_key else {}

    def _ensure_collection(self, collection: str) -> None:
        with httpx.Client(timeout=15, headers=self._headers) as client:
            client.put(f"{self._url}/collections/{collection}")

    def upsert(self, collection: str, items: list[dict[str, Any]]) -> None:
        self._ensure_collection(collection)
        points = [{"id": it["id"], "vector": it["vector"], "payload": it.get("payload", {})}
                  for it in items]
        with httpx.Client(timeout=30, headers=self._headers) as client:
            client.post(f"{self._url}/collections/{collection}/points?wait=true",
                        json={"points": points})

    def search(self, collection: str, vector: list[float], limit: int = 5,
               flt: Filter = None) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"query": vector, "limit": limit, "with_payload": True}
        if flt:
            must = [{"key": k, "match": {"value": v}} for k, v in flt.items() if not k.startswith("$")]
            if must:
                body["filter"] = {"must": must}
        with httpx.Client(timeout=15, headers=self._headers) as client:
            resp = client.post(f"{self._url}/collections/{collection}/points/query", json=body)
            if resp.status_code >= 400:  # older qdrant fallback
                resp = client.post(f"{self._url}/collections/{collection}/points/search",
                                   json={"vector": vector, "limit": limit, "with_payload": True,
                                         **({"filter": body["filter"]} if "filter" in body else {})})
            resp.raise_for_status()
        out = []
        for row in resp.json().get("result", {}).get("points", []):
            out.append({"id": row.get("id"), "score": round(row.get("score", 0.0), 4),
                        "payload": row.get("payload", {})})
        return out

    def count(self, collection: str) -> int:
        with httpx.Client(timeout=15, headers=self._headers) as client:
            resp = client.post(f"{self._url}/collections/{collection}/points/count", json={"exact": True})
            if resp.status_code >= 400:
                return 0
            return int(resp.json().get("result", {}).get("count", 0))

    def status(self) -> dict[str, Any]:
        return {"backend": "qdrant", "url": self._url, "collections": {}}


class MilvusVectorStore:
    backend = "milvus"

    def __init__(self) -> None:
        s = get_settings()
        self._url = s.milvus_uri.rstrip("/")
        self._headers = {"Authorization": f"Bearer {s.milvus_token}"} if s.milvus_token else {}

    def _ensure_collection(self, collection: str, dim: int) -> None:
        with httpx.Client(timeout=15, headers=self._headers) as client:
            client.post(f"{self._url}/v2/vectordb/collections/create", json={
                "collectionName": collection, "dimension": dim,
                "autoId": False, "metricType": "COSINE"})

    def upsert(self, collection: str, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        self._ensure_collection(collection, len(items[0]["vector"]))
        data = {"collectionName": collection,
                "data": [{"id": it["id"], "vector": it["vector"],
                          "payload": json.dumps(it.get("payload", {}))} for it in items]}
        with httpx.Client(timeout=30, headers=self._headers) as client:
            client.post(f"{self._url}/v2/vectordb/entities/upsert", json=data)

    def search(self, collection: str, vector: list[float], limit: int = 5,
               flt: Filter = None) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"collectionName": collection, "data": [vector],
                                "limit": limit, "outputFields": ["payload"]}
        with httpx.Client(timeout=15, headers=self._headers) as client:
            resp = client.post(f"{self._url}/v2/vectordb/entities/search", json=body)
            resp.raise_for_status()
        return [{"id": row.get("id"), "score": round(row.get("distance", 0.0), 4),
                 "payload": json.loads(row.get("payload") or "{}")}
                for row in resp.json().get("data", [])]

    def count(self, collection: str) -> int:
        with httpx.Client(timeout=15, headers=self._headers) as client:
            resp = client.post(f"{self._url}/v2/vectordb/collections/get_stats",
                               json={"collectionName": collection})
            if resp.status_code >= 400:
                return 0
            return int(resp.json().get("data", {}).get("rowCount", 0))

    def status(self) -> dict[str, Any]:
        return {"backend": "milvus", "uri": self._url, "collections": {}}


_STORE: Any = None


def get_vector_store() -> Any:
    global _STORE
    if _STORE is None:
        backend = get_settings().vector_store.lower()
        if backend == "qdrant":
            _STORE = QdrantVectorStore()
        elif backend == "milvus":
            _STORE = MilvusVectorStore()
        else:
            _STORE = LocalVectorStore()
    return _STORE
