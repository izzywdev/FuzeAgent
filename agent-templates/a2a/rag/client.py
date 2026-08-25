"""Retrieval against the shared Chroma instance. RETRIEVAL ONLY — never indexing.

The boundary matters. Indexing needs the original documents, and those live with
whoever owns them (FuzeAgent's orchestrator keeps them on a filesystem under
KNOWLEDGE_STORAGE_PATH). The A2A server is a multi-tenant pod that must not hold
any tenant's document store, so it never writes: it embeds a query, asks Chroma,
and returns the chunk text Chroma already carries.

That last part is why no document database is needed here. The indexer stores the
chunk TEXT alongside the vector (`collection.add(..., documents=text_chunks)`),
and the query asks for it back (`include=["documents", ...]`). A second hop to
Mongo or Postgres to re-fetch the source would be needed only if Chroma held
vectors alone — it does not. The document store is for re-indexing and download,
not for answering a query.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import RagConfig
from .errors import RagUnavailable

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Chunk:
    """One retrieved passage. `score` is cosine similarity in [0, 1]."""

    document_id: str
    chunk_index: int
    content: str
    score: float
    metadata: dict


class RagRetriever:
    """Chroma-backed retrieval for one A2A deployment.

    Connects EAGERLY at construction. A lazy connection would move the failure to
    the first query, where it reads as "no results" — the exact confusion this
    package exists to remove.
    """

    def __init__(self, config: RagConfig, *, client=None, embedder=None):
        self.config = config
        self._embedder = embedder
        self._client = client if client is not None else self._connect()

    def _connect(self):
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - dependency is declared
            raise RagUnavailable(
                "chromadb is not installed but RAG is enabled; the image is built "
                "without its retrieval dependency"
            ) from exc
        c = self.config
        try:
            return chromadb.HttpClient(
                host=c.host,
                port=c.port,
                ssl=c.ssl,
                tenant=c.tenant,
                database=c.database,
                settings=c.chroma_settings(),
            )
        except Exception as exc:
            # Re-raised, never swallowed. A pod that cannot reach its vector store
            # should fail its readiness probe, not serve confident empty answers.
            raise RagUnavailable(
                f"cannot reach Chroma at {c.host}:{c.port} "
                f"(database={c.database!r}): {exc}"
            ) from exc

    def _embed(self, query: str) -> list[float]:
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover
                raise RagUnavailable(
                    "sentence-transformers is not installed but RAG is enabled"
                ) from exc
            self._embedder = SentenceTransformer(self.config.embedding_model)
        return self._embedder.encode(query).tolist()

    def search(self, tenant: str, query: str, *, limit: int = 5,
               min_score: float = 0.0) -> list[Chunk]:
        """Chunks for `tenant`, most similar first.

        An empty list means the corpus had nothing above `min_score`. It never
        means the store was unreachable — that raises RagUnavailable.
        """
        if not query or not query.strip():
            return []
        name = self.config.collection_for(tenant)
        try:
            collection = self._client.get_collection(name=name)
        except Exception as exc:
            # A tenant with no collection has simply indexed nothing. That IS an
            # empty corpus, so it is an empty result rather than an error — but it
            # is logged, because "this tenant has no collection" and "this tenant's
            # collection is empty" are worth telling apart in a transcript.
            log.info("no Chroma collection %r for tenant %r (%s); empty corpus",
                     name, tenant, exc)
            return []
        try:
            res = collection.query(
                query_embeddings=[self._embed(query)],
                n_results=limit,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise RagUnavailable(f"query against {name!r} failed: {exc}") from exc

        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        out: list[Chunk] = []
        for doc, meta, dist in zip(docs, metas, dists):
            meta = meta or {}
            score = 1.0 - float(dist)
            if score < min_score:
                continue
            out.append(Chunk(
                document_id=str(meta.get("document_id", "")),
                chunk_index=int(meta.get("chunk_index", 0) or 0),
                content=doc,
                score=score,
                metadata=dict(meta),
            ))
        return out

    def healthcheck(self) -> None:
        """Raise RagUnavailable unless the store answers. Used by readiness."""
        try:
            self._client.heartbeat()
        except Exception as exc:
            raise RagUnavailable(f"Chroma heartbeat failed: {exc}") from exc
