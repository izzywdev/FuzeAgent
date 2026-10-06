"""
pgvector-backed document store for the Brains wiki (Track #4).

Documents are chunked-free for simplicity: one embedding per document
(title + content), stored in `brain_documents` with a vector(384) column and
searched by cosine distance. Falls back to the caller's in-memory data when the
database or embedding model is unavailable, so the API never hard-fails.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

try:
    from .database import get_db_connection
except ImportError:
    from database import get_db_connection

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384
_model = None
_table_ready = False


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


async def _embed(text: str) -> List[float]:
    loop = asyncio.get_event_loop()
    vec = await loop.run_in_executor(
        None, lambda: _get_model().encode(text, normalize_embeddings=True).tolist()
    )
    return vec


def _vec_literal(vec: List[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


async def _ensure_table(conn) -> None:
    global _table_ready
    if _table_ready:
        return
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS brain_documents (
            id TEXT PRIMARY KEY,
            brain_id TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'General',
            content TEXT NOT NULL,
            author TEXT NOT NULL DEFAULT 'unknown',
            tags TEXT[] NOT NULL DEFAULT '{}',
            embedding vector(384),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_brain_documents_brain ON brain_documents(brain_id)"
    )
    _table_ready = True


def _row_to_doc(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "content": row["content"],
        "author": row["author"],
        "updatedAt": row["created_at"].isoformat() if row["created_at"] else "",
        "tags": list(row["tags"] or []),
        "chunksCount": max(1, len(row["content"]) // 250),
    }


async def list_documents(brain_id: str) -> Optional[List[Dict[str, Any]]]:
    """Return stored docs for a brain, or None if the store is unavailable."""
    try:
        async with get_db_connection() as conn:
            await _ensure_table(conn)
            rows = await conn.fetch(
                "SELECT id, title, category, content, author, tags, created_at "
                "FROM brain_documents WHERE brain_id = $1 ORDER BY created_at DESC",
                brain_id,
            )
            return [_row_to_doc(r) for r in rows]
    except Exception as e:
        logger.warning(f"brain_store.list_documents unavailable: {e}")
        return None


async def add_document(
    brain_id: str,
    title: str,
    content: str,
    category: str = "General",
    author: str = "unknown",
    tags: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Embed and persist a document. Returns the doc, or None if unavailable."""
    try:
        vec = await _embed(f"{title}\n{content}")
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        async with get_db_connection() as conn:
            await _ensure_table(conn)
            row = await conn.fetchrow(
                "INSERT INTO brain_documents "
                "(id, brain_id, title, category, content, author, tags, embedding) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8::vector) "
                "RETURNING id, title, category, content, author, tags, created_at",
                doc_id,
                brain_id,
                title,
                category,
                content,
                author,
                tags or [],
                _vec_literal(vec),
            )
            return _row_to_doc(row)
    except Exception as e:
        logger.warning(f"brain_store.add_document unavailable: {e}")
        return None


async def search(
    brain_id: str, query: str, limit: int = 3
) -> Optional[List[Dict[str, Any]]]:
    """Cosine-similarity search. Returns docs with a `score`, or None if unavailable."""
    try:
        vec = await _embed(query)
        async with get_db_connection() as conn:
            await _ensure_table(conn)
            rows = await conn.fetch(
                "SELECT id, title, category, content, author, tags, created_at, "
                "1 - (embedding <=> $2::vector) AS score "
                "FROM brain_documents WHERE brain_id = $1 AND embedding IS NOT NULL "
                "ORDER BY embedding <=> $2::vector LIMIT $3",
                brain_id,
                _vec_literal(vec),
                limit,
            )
            out = []
            for r in rows:
                d = _row_to_doc(r)
                d["score"] = float(r["score"])
                out.append(d)
            return out
    except Exception as e:
        logger.warning(f"brain_store.search unavailable: {e}")
        return None
