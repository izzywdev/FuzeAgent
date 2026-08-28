"""Shared RAG retrieval for the A2A server image.

One Chroma instance (FuzeInfra's), one database allocated to A2A, one collection
per tenant. Retrieval only — see client.py for why indexing stays with whoever
owns the documents.

    from a2a.rag import build_from_env, RagUnavailable

    retriever = build_from_env()      # None when RAG is deliberately disabled
    if retriever:
        chunks = retriever.search("FuzeAgent", "how does auth work?")
"""

from .client import Chunk, RagRetriever
from .config import RagConfig, from_env as config_from_env
from .errors import RagConfigError, RagError, RagUnavailable

__all__ = [
    "Chunk", "RagRetriever", "RagConfig", "RagConfigError", "RagError",
    "RagUnavailable", "build_from_env", "config_from_env",
]


def build_from_env(env: dict | None = None) -> RagRetriever | None:
    """Retriever from the environment, or None when RAG is disabled.

    None is returned ONLY for a deliberate opt-out (A2A_RAG_ENABLED unset).
    Enabled-but-misconfigured raises RagConfigError; enabled-but-unreachable
    raises RagUnavailable. Neither is degraded into a working-looking retriever
    that answers every question with nothing.
    """
    config = config_from_env(env)
    if config is None:
        return None
    return RagRetriever(config)
