"""Tests for a2a.rag.

Weighted toward the two failures that made FuzeAgent's RAG inert in production
for months while every log line and health probe looked fine:

  1. `chroma_client_auth_provider="basic"` — not a resolvable class path, so the
     client was built with no auth despite appearing to configure it.
  2. `CHROMA_HOST` defaulting to "localhost" with nothing setting it, and a broad
     `except Exception` turning the resulting connection failure into
     `collection = None` — after which every search returned empty and nothing,
     anywhere, could tell that apart from an empty corpus.

So the assertions here are mostly that this package REFUSES, and that
unreachable never presents as empty.
"""

import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from a2a.rag import config as ragconfig  # noqa: E402
from a2a.rag.client import RagRetriever  # noqa: E402
from a2a.rag.errors import RagConfigError, RagUnavailable  # noqa: E402


BASE = {
    "A2A_RAG_ENABLED": "1",
    "CHROMA_HOST": "chroma.fuzeinfra.svc.cluster.local",
    "CHROMA_DATABASE": "a2a",
    "CHROMA_AUTH_TOKEN": "t0ken",
}


class ConfigTests(unittest.TestCase):
    def test_disabled_is_the_only_silent_outcome(self):
        self.assertIsNone(ragconfig.from_env({}))
        self.assertIsNone(ragconfig.from_env({"A2A_RAG_ENABLED": "0"}))

    def test_enabled_without_a_host_refuses_instead_of_using_localhost(self):
        """The exact production defect: enabled, no CHROMA_HOST, silently local."""
        env = dict(BASE)
        del env["CHROMA_HOST"]
        with self.assertRaises(RagConfigError) as ctx:
            ragconfig.from_env(env)
        self.assertIn("CHROMA_HOST", str(ctx.exception))
        self.assertIn("localhost", str(ctx.exception))

    def test_enabled_without_a_database_refuses(self):
        """The instance is shared; landing in the default namespace is a leak."""
        env = dict(BASE)
        del env["CHROMA_DATABASE"]
        with self.assertRaises(RagConfigError):
            ragconfig.from_env(env)

    def test_enabled_without_a_credential_refuses(self):
        """An absent credential must not be read as 'this instance has no auth'."""
        env = dict(BASE)
        del env["CHROMA_AUTH_TOKEN"]
        with self.assertRaises(RagConfigError) as ctx:
            ragconfig.from_env(env)
        self.assertIn("CHROMA_ALLOW_UNAUTHENTICATED", str(ctx.exception))

    def test_unauthenticated_must_be_stated_out_loud(self):
        env = dict(BASE)
        del env["CHROMA_AUTH_TOKEN"]
        env["CHROMA_ALLOW_UNAUTHENTICATED"] = "1"
        cfg = ragconfig.from_env(env)
        self.assertIsNone(cfg.auth_provider)

    def test_auth_provider_is_a_class_path_not_the_word_basic(self):
        """Guards against re-typing the literal that shipped broken."""
        cfg = ragconfig.from_env(BASE)
        self.assertEqual(cfg.auth_provider, ragconfig.TOKEN_AUTH_PROVIDER)
        self.assertIn(".", cfg.auth_provider)
        self.assertNotEqual(cfg.auth_provider, "basic")
        self.assertNotEqual(cfg.auth_provider, "token")

    def test_basic_auth_requires_user_colon_password(self):
        env = dict(BASE)
        del env["CHROMA_AUTH_TOKEN"]
        env["CHROMA_AUTH_BASIC"] = "no-colon-here"
        with self.assertRaises(RagConfigError):
            ragconfig.from_env(env)
        env["CHROMA_AUTH_BASIC"] = "user:pw"
        self.assertEqual(ragconfig.from_env(env).auth_provider,
                         ragconfig.BASIC_AUTH_PROVIDER)

    def test_two_credentials_is_ambiguous_and_refused(self):
        env = dict(BASE, CHROMA_AUTH_BASIC="user:pw")
        with self.assertRaises(RagConfigError):
            ragconfig.from_env(env)

    def test_tenants_get_separate_collections_not_a_shared_one_with_a_filter(self):
        cfg = ragconfig.from_env(BASE)
        self.assertNotEqual(cfg.collection_for("FuzeAgent"), cfg.collection_for("FuzeBI"))
        self.assertEqual(cfg.collection_for("FuzeAgent"), "a2a-fuzeagent")
        self.assertEqual(cfg.collection_for("Fuze Front!"), "a2a-fuze-front-")


class _FakeCollection:
    def __init__(self, result=None, raises=None):
        self._result, self._raises = result, raises

    def query(self, **_kw):
        if self._raises:
            raise self._raises
        return self._result


class _FakeClient:
    def __init__(self, collection=None, get_raises=None, beat_raises=None):
        self._collection, self._get_raises = collection, get_raises
        self._beat_raises = beat_raises

    def get_collection(self, name):
        if self._get_raises:
            raise self._get_raises
        return self._collection

    def heartbeat(self):
        if self._beat_raises:
            raise self._beat_raises
        return 1


class _FakeEmbedder:
    def encode(self, _text):
        return types.SimpleNamespace(tolist=lambda: [0.1, 0.2, 0.3])


def _retriever(client):
    return RagRetriever(ragconfig.from_env(BASE), client=client,
                        embedder=_FakeEmbedder())


class RetrievalTests(unittest.TestCase):
    def test_a_failed_query_raises_and_never_returns_empty(self):
        """THE regression. Empty means 'nothing matched', never 'no connection'."""
        r = _retriever(_FakeClient(_FakeCollection(raises=RuntimeError("boom"))))
        with self.assertRaises(RagUnavailable):
            r.search("FuzeAgent", "anything")

    def test_a_tenant_with_no_collection_is_an_empty_corpus_not_an_error(self):
        r = _retriever(_FakeClient(get_raises=ValueError("not found")))
        self.assertEqual(r.search("FuzeAgent", "anything"), [])

    def test_results_are_scored_and_filtered(self):
        result = {
            "documents": [["near", "far"]],
            "metadatas": [[{"document_id": "d1", "chunk_index": 0},
                           {"document_id": "d2", "chunk_index": 3}]],
            "distances": [[0.1, 0.9]],
        }
        r = _retriever(_FakeClient(_FakeCollection(result)))
        chunks = r.search("FuzeAgent", "q", min_score=0.5)
        self.assertEqual([c.content for c in chunks], ["near"])
        self.assertAlmostEqual(chunks[0].score, 0.9)
        self.assertEqual(chunks[0].document_id, "d1")

    def test_chunk_text_comes_back_from_chroma_so_no_document_store_is_needed(self):
        """`documents` is requested and used — no second hop to Mongo/Postgres."""
        result = {"documents": [["the passage text"]],
                  "metadatas": [[{"document_id": "d1", "chunk_index": 0}]],
                  "distances": [[0.0]]}
        r = _retriever(_FakeClient(_FakeCollection(result)))
        self.assertEqual(r.search("FuzeAgent", "q")[0].content, "the passage text")

    def test_blank_query_short_circuits(self):
        r = _retriever(_FakeClient(_FakeCollection({"documents": [[]]})))
        self.assertEqual(r.search("FuzeAgent", "   "), [])

    def test_healthcheck_raises_so_readiness_can_fail(self):
        ok = _retriever(_FakeClient(beat_raises=None))
        ok.healthcheck()
        bad = _retriever(_FakeClient(beat_raises=OSError("refused")))
        with self.assertRaises(RagUnavailable):
            bad.healthcheck()


if __name__ == "__main__":
    unittest.main(verbosity=2)
