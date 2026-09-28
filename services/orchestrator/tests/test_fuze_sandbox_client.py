import base64

import httpx
import pytest
from services.orchestrator.fuze_sandbox_client import (
    FuzeSandboxClient,
    FuzeSandboxError,
)


@pytest.mark.asyncio
async def test_client_supports_jobs_and_workspace_operations_without_env_injection():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.headers["Authorization"] == "Bearer service-api-key"
        if request.url.path == "/v1/sandboxes":
            payload = __import__("json").loads(request.content)
            assert payload["kind"] in {"job", "workspace"}
            assert "environment" not in payload
            return httpx.Response(202, json={"id": "remote-1", "status": "pending"})
        if request.url.path == "/readyz":
            return httpx.Response(
                200,
                json={
                    "status": "ready",
                    "execution_enabled": True,
                    "worker": "ready",
                    "machine_workspace_enabled": True,
                },
            )
        if request.url.path.endswith("/exec"):
            return httpx.Response(200, json={"sandbox_id": "remote-1", "output": "ok"})
        if request.method == "POST" and request.url.path.endswith("/files"):
            payload = __import__("json").loads(request.content)
            assert base64.b64decode(payload["content_base64"]) == b"source"
            return httpx.Response(200, json={"status": "completed"})
        if request.method == "GET" and request.url.path.endswith("/files"):
            return httpx.Response(
                200, json={"content_base64": base64.b64encode(b"result").decode()}
            )
        if request.url.path.endswith("/preview-grants"):
            return httpx.Response(
                201, json={"url": "https://api.example/preview/token"}
            )
        if request.url.path.endswith("/cancel"):
            return httpx.Response(202, json={"status": "deleting"})
        if request.url.path.endswith("/logs"):
            return httpx.Response(200, json={"logs": "job output"})
        return httpx.Response(200, json={"id": "remote-1", "status": "running"})

    client = FuzeSandboxClient(
        "https://sandbox.example",
        "service-api-key",
        transport=httpx.MockTransport(handler),
    )
    try:
        job = await client.create_sandbox(
            name="job", image="image", kind="job", command=["echo", "ok"]
        )
        workspace = await client.create_sandbox(
            name="work", image="image", kind="workspace", ports=[3000]
        )
        assert job["id"] == workspace["id"] == "remote-1"
        assert (await client.get_readiness())["machine_workspace_enabled"] is True
        assert (await client.get_sandbox("remote-1"))["status"] == "running"
        assert (await client.get_logs("remote-1"))["logs"] == "job output"
        assert (await client.execute_workspace("remote-1", "id"))["output"] == "ok"
        await client.write_workspace_file("remote-1", "/workspace/main.py", b"source")
        assert (
            await client.read_workspace_file("remote-1", "/workspace/result.txt")
            == b"result"
        )
        assert (await client.create_preview_grant("remote-1", 3000))["url"].startswith(
            "https://"
        )
        assert (await client.cancel_sandbox("remote-1"))["status"] == "deleting"
        assert len(calls) == 10
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_client_errors_are_sanitized_and_file_size_is_bounded():
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, json={"detail": "secret response body must not escape"}
        )

    client = FuzeSandboxClient(
        "https://sandbox.example",
        "do-not-log-this",
        transport=httpx.MockTransport(handler),
    )
    try:
        with pytest.raises(FuzeSandboxError) as error:
            await client.get_sandbox("remote-1")
        assert "403" in str(error.value)
        assert "do-not-log-this" not in str(error.value)
        assert "secret response body" not in str(error.value)
        with pytest.raises(ValueError):
            await client.write_workspace_file(
                "remote-1", "/workspace/large", b"x" * 1_000_001
            )
    finally:
        await client.close()
