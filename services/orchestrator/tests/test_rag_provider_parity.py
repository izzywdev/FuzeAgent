"""The two Chroma auth-provider constants must not drift apart.

`services/orchestrator/rag_integration.py` (the indexer) and
`agent-templates/a2a/rag/config.py` (the shared A2A retriever) connect to the
SAME Chroma instance and cannot import each other — the orchestrator image is
built with context `services/orchestrator`, the A2A image with context
`agent-templates`, so neither tree is present in the other's build.

Duplication across that boundary is unavoidable. Silent duplication is not: the
literal that shipped broken (`chroma_client_auth_provider="basic"`) is exactly
the kind of value that gets re-typed from memory in a second place. This test is
the thing that makes the copy visible, so it must fail loudly if they diverge.
"""

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ProviderParityTests(unittest.TestCase):
    def setUp(self):
        shared = REPO / "agent-templates" / "a2a" / "rag" / "config.py"
        if not shared.is_file():
            self.skipTest(f"shared a2a rag config not present at {shared}")
        # Imported by path, not as a package: `a2a.rag.config` pulls in the whole
        # a2a package, whose deps are not installed in the orchestrator's image.
        self.shared = _load(shared, "_a2a_rag_config")

    def test_token_provider_matches(self):
        from rag_integration import TOKEN_AUTH_PROVIDER

        self.assertEqual(TOKEN_AUTH_PROVIDER, self.shared.TOKEN_AUTH_PROVIDER)

    def test_basic_provider_matches(self):
        from rag_integration import BASIC_AUTH_PROVIDER

        self.assertEqual(BASIC_AUTH_PROVIDER, self.shared.BASIC_AUTH_PROVIDER)

    def test_neither_is_a_bare_keyword(self):
        """Chroma resolves this string as an import path. 'basic' resolves to nothing."""
        for value in (self.shared.TOKEN_AUTH_PROVIDER, self.shared.BASIC_AUTH_PROVIDER):
            self.assertIn(".", value, f"{value!r} is not a dotted class path")
            self.assertTrue(value.startswith("chromadb.auth."), value)
