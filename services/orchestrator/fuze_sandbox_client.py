"""Small async client for the Fuze Sandbox machine API.

The API key is held by the FuzeAgent service and is never sent to a sandbox.
"""

from __future__ import annotations

import base64

import httpx


class FuzeSandboxError(RuntimeError):
    def __init__(self, status_code: int, operation: str):
        super().__init__(f"Fuze Sandbox {operation} failed with HTTP {status_code}")
        self.status_code = status_code


class FuzeSandboxClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not base_url or not api_key:
            raise ValueError("Fuze Sandbox base URL and API key are required")
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def get_readiness(self) -> dict:
        return await self._request("readiness", "GET", "/readyz")

    async def _request(self, operation: str, method: str, path: str, **kwargs):
        response = await self._http.request(method, path, **kwargs)
        if not response.is_success:
            raise FuzeSandboxError(response.status_code, operation)
        if response.status_code == 204:
            return None
        return response.json()

    async def create_sandbox(
        self,
        *,
        name: str,
        image: str,
        kind: str,
        profile: str = "agent-small",
        ttl_seconds: int = 3600,
        storage: str = "5Gi",
        ports: list[int] | None = None,
        command: list[str] | None = None,
        args: list[str] | None = None,
    ) -> dict:
        return await self._request(
            "create",
            "POST",
            "/v1/sandboxes",
            json={
                "name": name,
                "image": image,
                "kind": kind,
                "profile": profile,
                "ttl_seconds": ttl_seconds,
                "storage": storage,
                "ports": ports or [],
                "command": command or [],
                "args": args or [],
            },
        )

    async def get_sandbox(self, sandbox_id: str) -> dict:
        return await self._request("get sandbox", "GET", f"/v1/sandboxes/{sandbox_id}")

    async def list_sandboxes(self) -> list[dict]:
        return await self._request("list sandboxes", "GET", "/v1/sandboxes")

    async def get_logs(self, sandbox_id: str) -> dict:
        return await self._request(
            "get logs", "GET", f"/v1/sandboxes/{sandbox_id}/logs"
        )

    async def cancel_sandbox(self, sandbox_id: str) -> dict:
        return await self._request(
            "cancel", "POST", f"/v1/sandboxes/{sandbox_id}/cancel"
        )

    async def execute_workspace(self, sandbox_id: str, command: str) -> dict:
        return await self._request(
            "workspace command",
            "POST",
            f"/v1/sandboxes/{sandbox_id}/exec",
            json={"command": command},
        )

    async def write_workspace_file(
        self, sandbox_id: str, path: str, content: bytes
    ) -> dict:
        if len(content) > 1_000_000:
            raise ValueError("workspace file content is limited to 1 MB")
        encoded = base64.b64encode(content).decode("ascii")
        return await self._request(
            "workspace file write",
            "POST",
            f"/v1/sandboxes/{sandbox_id}/files",
            json={"path": path, "content_base64": encoded},
        )

    async def read_workspace_file(self, sandbox_id: str, path: str) -> bytes:
        result = await self._request(
            "workspace file read",
            "GET",
            f"/v1/sandboxes/{sandbox_id}/files",
            params={"path": path},
        )
        return base64.b64decode(result["content_base64"], validate=True)

    async def create_preview_grant(self, sandbox_id: str, port: int) -> dict:
        return await self._request(
            "preview grant",
            "POST",
            f"/v1/sandboxes/{sandbox_id}/preview-grants",
            json={"port": port},
        )
