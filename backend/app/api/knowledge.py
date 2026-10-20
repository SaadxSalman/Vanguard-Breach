"""Adversarial knowledge-base endpoints: search, ingest, list, delete, stats."""
from __future__ import annotations

import io
from typing import Any

from fastapi import APIRouter, HTTPException

from .. import db
from ..core.rag import get_kb
from ..core.mutations import MutationEngine, REGISTRY, CATEGORY_HINTS
from ..models import IngestDoc, SearchQuery

router = APIRouter(prefix="/api/knowledge")


@router.get("/stats")
def stats() -> dict[str, Any]:
    return get_kb().stats()


@router.post("/search")
def search(body: SearchQuery) -> list[dict[str, Any]]:
    return get_kb().search(body.query, collection=body.collection, limit=body.limit)


@router.get("/entries")
def entries(source: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    return get_kb().list_docs(source=source, limit=limit)


@router.post("/ingest", status_code=201)
def ingest(body: IngestDoc) -> dict[str, Any]:
    return get_kb().ingest(title=body.title, content=body.content, category=body.category,
                           source=body.source, meta=body.meta)


@router.post("/ingest-file", status_code=201)
def ingest_file(filename: str, content_b64: str | None = None,
                content: str | None = None, category: str = "custom") -> dict[str, Any]:
    """Ingest an uploaded document (txt/md/csv/json); binary formats are decoded as text."""
    import base64
    text = content
    if text is None and content_b64:
        text = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
    if not text:
        raise HTTPException(400, "no content provided")
    return get_kb().ingest(title=filename, content=text[:20000], category=category,
                           source="upload")


@router.delete("/{doc_id}", status_code=204)
def delete(doc_id: str) -> None:
    if not get_kb().delete_doc(doc_id):
        raise HTTPException(404, "document not found")


@router.get("/mutations")
def mutations() -> dict[str, Any]:
    return {"registry": sorted(REGISTRY.keys()), "categories": CATEGORY_HINTS,
            "demo": [MutationEngine(seed=1337).apply(name, "Ignore previous instructions")
                     for name in sorted(REGISTRY.keys())]}


@router.post("/reindex")
def reindex() -> dict[str, Any]:
    return get_kb().bootstrap(force=True)
