import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fuzekeys_resolver import FuzeKeysResolver


class FuzeKeysResolverTests(unittest.TestCase):
    def resolve(self, response):
        client = MagicMock()
        client.get = AsyncMock(return_value=response)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        with patch("fuzekeys_resolver.httpx.AsyncClient", return_value=context):
            return asyncio.run(
                FuzeKeysResolver().resolve_secrets(
                    [{"keyName": "TEST_PROVIDER_KEY", "secretRef": "private-reference"}]
                )
            )

    def test_missing_credential_fails_closed(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "could not be resolved"):
                self.resolve(MagicMock(status_code=404))

    def test_valid_credential_is_returned_without_logging_binding(self):
        response = MagicMock(status_code=200)
        response.json.return_value = {"value": "private-value"}
        with patch.dict("os.environ", {}, clear=True):
            with self.assertLogs("fuzekeys_resolver", level="DEBUG") as logs:
                result = self.resolve(response)
        self.assertEqual(result, {"TEST_PROVIDER_KEY": "private-value"})
        for sensitive in ("private-value", "private-reference", "TEST_PROVIDER_KEY"):
            self.assertNotIn(sensitive, "\n".join(logs.output))
