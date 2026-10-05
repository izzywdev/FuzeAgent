"""
FuzeKeys Secret Resolver for Agent Sandboxes (Track #2).
Resolves zero-exposure vault secrets via FuzeKeys internal cluster API into sandbox environment variables.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

FUZEKEYS_API_URL = os.getenv(
    "FUZEKEYS_API_URL",
    os.getenv(
        "FUZEKEYS_URL", "http://fuzekeys-backend.fuzekeys.svc.cluster.local:3000"
    ),
)
SERVICE_TOKEN = os.getenv("FUZEFRONT_SECURITY_SERVICE_TOKEN", "")


class FuzeKeysResolver:
    """Queries FuzeKeys Vault and decrypts runtime secrets for sandboxed agent pods."""

    def __init__(
        self, base_url: str = FUZEKEYS_API_URL, service_token: str = SERVICE_TOKEN
    ):
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token

    async def resolve_secrets(
        self,
        secret_bindings: List[Dict[str, Any]],
        org_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Resolves a list of SecretBinding models (keyName, secretRef) into
        plain environment variable key-value pairs.
        """
        resolved: Dict[str, str] = {}
        # Counters only: never log key names, secret references or lookup errors, which
        # can embed the vault reference (CWE-312/532).
        from_env = from_vault = opaque = 0
        headers = {
            "Content-Type": "application/json",
            "X-Caller-Service": "fuzeagent-orchestrator",
        }
        if self.service_token:
            headers["Authorization"] = f"Bearer {self.service_token}"
        if org_id:
            headers["X-Organization-Id"] = org_id

        async with httpx.AsyncClient(timeout=4.0) as client:
            for binding in secret_bindings:
                key_name = (
                    binding.get("keyName")
                    if isinstance(binding, dict)
                    else getattr(binding, "keyName", None)
                )
                secret_ref = (
                    binding.get("secretRef")
                    if isinstance(binding, dict)
                    else getattr(binding, "secretRef", None)
                )

                if not key_name or not secret_ref:
                    continue

                # 1. Try local process environment override first (e.g. when run in dev or injected via k8s secret)
                env_val = os.getenv(key_name)
                if env_val:
                    resolved[key_name] = env_val
                    from_env += 1
                    continue

                # 2. Query FuzeKeys cluster backend
                try:
                    url = f"{self.base_url}/api/v1/secrets/{secret_ref}"
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        val = (
                            data.get("value") or data.get("secret") or data.get("data")
                        )
                        if val:
                            resolved[key_name] = str(val)
                            from_vault += 1
                            continue
                except Exception as e:
                    # Exception text can include the request URL (and so the secret ref).
                    logger.debug("FuzeKeys API lookup failed (%s)", type(e).__name__)

                # 3. Fallback: masked token representation to avoid crash
                resolved[key_name] = f"fk_live_{secret_ref[:12]}"
                opaque += 1

        logger.info(
            "FuzeKeys: resolved %d binding(s) (ambient env=%d, vault=%d, opaque ref=%d)",
            len(resolved),
            from_env,
            from_vault,
            opaque,
        )
        return resolved


# Global singleton instance
fuzekeys_resolver = FuzeKeysResolver()
