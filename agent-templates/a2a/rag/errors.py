"""RAG failure modes, kept distinct because conflating them is the defect.

`services/orchestrator/rag_integration.py` wrapped connect-time failure in a
broad `except Exception` that set `chroma_client = None` and carried on. Every
later search then returned an empty result — indistinguishable, to the caller
and to an operator reading a transcript, from "the corpus genuinely has nothing
relevant". RAG was inert in production for as long as that was true, and the
only trace was one log line at startup.

So: a retriever that cannot reach its store RAISES. It never returns `[]`.
"""


class RagError(Exception):
    """Base for everything in this package."""


class RagConfigError(RagError):
    """The configuration is incoherent — raised at construction, before serving.

    Deliberately fatal rather than degraded. A RAG-enabled deployment missing
    CHROMA_HOST is a deploy defect, and the useful moment to say so is the pod's
    first seconds, not silently on every query afterwards.
    """


class RagUnavailable(RagError):
    """The store is configured but unreachable, or the query failed.

    Distinct from "no matching chunks", which is an ordinary empty list.
    """
