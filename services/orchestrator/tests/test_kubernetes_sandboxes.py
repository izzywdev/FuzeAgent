"""
Unit & Integration Tests for Kubernetes Sandbox Driver, Container Image Registry, and Multi-Agent Streaming.
Tests Track #1 (Kubernetes Pod Sandbox Lifecycle), Track #2 (Secret & NetworkPolicy Injection),
and REST/WebSocket endpoints for agent sandboxes.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from kubernetes.client.rest import ApiException

from image_registry_router import ACTIVE_SANDBOXES, TEMPLATES_REGISTRY, router
from kubernetes_sandbox_driver import KubernetesSandboxDriver


# ---------------------------------------------------------------------------
# Test Fixtures & App Setup
# ---------------------------------------------------------------------------
@pytest.fixture
def test_app():
    app = FastAPI(title="FuzeAgent Sandbox Test API")
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


# ---------------------------------------------------------------------------
# Test Suite 1: KubernetesSandboxDriver (Simulation Mode)
# ---------------------------------------------------------------------------
class TestKubernetesSandboxDriverSimulation:
    """Tests driver fallback when no active K8s cluster is present."""

    @pytest.mark.asyncio
    async def test_spawn_simulated_pod(self):
        driver = KubernetesSandboxDriver(namespace="test-namespace")
        driver.k8s_core_api = None
        driver.k8s_network_api = None

        res = await driver.spawn_sandbox_pod(
            template_id="python-dev-v2",
            image="ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest",
            env_vars={"CUSTOM_VAR": "value123"},
            secrets={"API_KEY": "secret_abc"},
            setup_script="echo 'testing'",
            network_isolation="outbound-only",
            timeout_seconds=900,
            ws_relay_url="wss://relay.example.com",
            agent_id="test-agent-1",
        )

        assert res["status"] == "running"
        assert res["mode"] == "simulated_pod"
        assert res["namespace"] == "test-namespace"
        assert (
            res["image"] == "ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest"
        )
        assert res["timeoutSeconds"] == 900
        assert res["podName"].startswith("agent-sbx-python-dev")
        assert res["secretName"] == f"{res['podName']}-sec"
        assert res["networkPolicyName"] == f"{res['podName']}-netpol"

    @pytest.mark.asyncio
    async def test_terminate_simulated_pod(self):
        driver = KubernetesSandboxDriver(namespace="test-namespace")
        driver.k8s_core_api = None
        driver.k8s_network_api = None

        result = await driver.terminate_sandbox_pod(
            pod_name="agent-sbx-sim-123",
            secret_name="agent-sbx-sim-123-sec",  # nosec B106
            netpol_name="agent-sbx-sim-123-netpol",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_list_and_logs_simulated_pod(self):
        driver = KubernetesSandboxDriver(namespace="test-namespace")
        driver.k8s_core_api = None

        pods = await driver.list_sandbox_pods()
        assert pods == []

        logs = await driver.get_sandbox_logs("agent-sbx-test")
        assert "[SIMULATED LOGS]" in logs
        assert "agent-sbx-test" in logs


# ---------------------------------------------------------------------------
# Test Suite 2: KubernetesSandboxDriver (Mocked Native K8s API)
# ---------------------------------------------------------------------------
class TestKubernetesSandboxDriverNative:
    """Tests native K8s resource generation (Secret, NetworkPolicy, Pod spec)."""

    @pytest.mark.asyncio
    async def test_spawn_sandbox_pod_creates_secret_and_networkpolicy(self):
        driver = KubernetesSandboxDriver(namespace="fuzeagent-test")
        mock_core = MagicMock()
        mock_network = MagicMock()
        driver.k8s_core_api = mock_core
        driver.k8s_network_api = mock_network

        res = await driver.spawn_sandbox_pod(
            template_id="react-dev-v2",
            image="ghcr.io/izzywdev/fuzeagent/claude-runner-react-dev:latest",
            env_vars={"NODE_ENV": "development"},
            secrets={
                "GITHUB_TOKEN": "ghp_mock123",  # nosec B105
                "AUTH_KEY": "sec_456",  # nosec B105
            },
            setup_script="npm test",
            network_isolation="outbound-only",
            timeout_seconds=1200,
            cpu_limit="4.0",
            memory_limit="8Gi",
            ws_relay_url="wss://bus.internal:8000/stream",
            agent_id="frontend-agent",
        )

        assert res["status"] == "running"
        assert res["mode"] == "k8s_pod"
        assert res["secretName"] is not None
        assert res["networkPolicyName"] is not None

        # 1. Verify Secret creation call
        assert mock_core.create_namespaced_secret.called
        secret_args = mock_core.create_namespaced_secret.call_args[1]
        assert secret_args["namespace"] == "fuzeagent-test"
        secret_body = secret_args["body"]
        assert secret_body["kind"] == "Secret"
        assert secret_body["stringData"]["GITHUB_TOKEN"] == "ghp_mock123"
        assert secret_body["stringData"]["AUTH_KEY"] == "sec_456"

        # 2. Verify NetworkPolicy creation call
        assert mock_network.create_namespaced_network_policy.called
        netpol_args = mock_network.create_namespaced_network_policy.call_args[1]
        assert netpol_args["namespace"] == "fuzeagent-test"
        netpol_body = netpol_args["body"]
        assert netpol_body["kind"] == "NetworkPolicy"
        assert "Ingress" in netpol_body["spec"]["policyTypes"]
        assert "Egress" in netpol_body["spec"]["policyTypes"]

        # Egress ports must include 53 (DNS) and 443 (HTTPS)
        egress_ports = [
            p.get("port")
            for rule in netpol_body["spec"]["egress"]
            for p in rule.get("ports", [])
        ]
        assert 53 in egress_ports
        assert 443 in egress_ports
        assert 8000 in egress_ports

        # 3. Verify Pod creation call
        assert mock_core.create_namespaced_pod.called
        pod_args = mock_core.create_namespaced_pod.call_args[1]
        pod_body = pod_args["body"]
        assert pod_body["kind"] == "Pod"
        assert pod_body["spec"]["activeDeadlineSeconds"] == 1200
        assert pod_body["spec"]["restartPolicy"] == "Never"

        container = pod_body["spec"]["containers"][0]
        assert (
            container["image"]
            == "ghcr.io/izzywdev/fuzeagent/claude-runner-react-dev:latest"
        )
        assert container["resources"]["limits"]["cpu"] == "4.0"
        assert container["resources"]["limits"]["memory"] == "8Gi"

        # Secret mounted via secretRef
        assert container["envFrom"] == [{"secretRef": {"name": res["secretName"]}}]

        # Env vars injected
        env_dict = {item["name"]: item["value"] for item in container["env"]}
        assert env_dict["NODE_ENV"] == "development"
        assert env_dict["WS_RELAY_URL"] == "wss://bus.internal:8000/stream"
        assert env_dict["AGENT_ID"] == "frontend-agent"
        assert env_dict["SETUP_SCRIPT"] == "npm test"

        # Startup command contains SETUP_SCRIPT execution
        assert container["command"][0] == "/bin/bash"
        assert 'eval "$SETUP_SCRIPT"' in container["command"][2]

    @pytest.mark.asyncio
    async def test_terminate_sandbox_pod_cleans_resources(self):
        driver = KubernetesSandboxDriver(namespace="fuzeagent-test")
        mock_core = MagicMock()
        mock_network = MagicMock()
        driver.k8s_core_api = mock_core
        driver.k8s_network_api = mock_network

        pod_name = "agent-sbx-test-99"
        sec_name = "agent-sbx-test-99-sec"
        netpol_name = "agent-sbx-test-99-netpol"

        result = await driver.terminate_sandbox_pod(
            pod_name=pod_name,
            secret_name=sec_name,
            netpol_name=netpol_name,
        )
        assert result is True

        mock_core.delete_namespaced_pod.assert_called_once_with(
            name=pod_name,
            namespace="fuzeagent-test",
            grace_period_seconds=0,
        )
        mock_core.delete_namespaced_secret.assert_called_once_with(
            name=sec_name,
            namespace="fuzeagent-test",
            grace_period_seconds=0,
        )
        mock_network.delete_namespaced_network_policy.assert_called_once_with(
            name=netpol_name,
            namespace="fuzeagent-test",
            grace_period_seconds=0,
        )

    @pytest.mark.asyncio
    async def test_terminate_tolerates_404_not_found(self):
        driver = KubernetesSandboxDriver(namespace="fuzeagent-test")
        mock_core = MagicMock()
        mock_network = MagicMock()

        # Simulate 404 ApiException on deletion
        not_found = ApiException(status=404, reason="Not Found")
        mock_core.delete_namespaced_pod.side_effect = not_found
        mock_core.delete_namespaced_secret.side_effect = not_found
        mock_network.delete_namespaced_network_policy.side_effect = not_found

        driver.k8s_core_api = mock_core
        driver.k8s_network_api = mock_network

        result = await driver.terminate_sandbox_pod("pod-123", "sec-123", "net-123")
        assert result is True


# ---------------------------------------------------------------------------
# Test Suite 3: REST Endpoints (Registry, Templates & Sandboxes)
# ---------------------------------------------------------------------------
class TestImageRegistryAndSandboxEndpoints:
    """Tests registry inspection and sandbox launch/terminate endpoints."""

    def test_list_registry_images(self, client: TestClient):
        response = client.get("/api/registry/images")
        assert response.status_code == 200
        data = response.json()
        assert data["registry"] in (
            "harbor.prod.fuzefront.com/sandboxes",
            "ghcr.io/izzywdev/fuzeagent",
        )
        assert isinstance(data["images"], list)
        assert len(data["images"]) >= 2

        # Check python-dev template image
        py_img = next(
            (img for img in data["images"] if img["templateId"] == "python-dev-v2"),
            None,
        )
        assert py_img is not None
        assert "claude-runner-python-dev:latest" in py_img["image"]
        assert py_img["status"] == "ready"
        assert py_img["networkIsolation"] == "outbound-only"
        assert py_img["secretBindingsCount"] >= 1
        assert py_img["dockerfile"] is True

    def test_get_template_image_status(self, client: TestClient):
        response = client.get("/api/templates/python-dev-v2/image-status")
        assert response.status_code == 200
        data = response.json()
        assert data["templateId"] == "python-dev-v2"
        assert data["status"] == "ready"
        assert data["hasDockerfile"] is True
        assert "claude-runner-python-dev:latest" in data["image"]
        assert "sandboxing" in data
        assert "secretBindings" in data

    def test_get_template_image_status_not_found(self, client: TestClient):
        response = client.get("/api/templates/non-existent-template/image-status")
        assert response.status_code == 404

    def test_launch_and_terminate_sandbox_lifecycle(self, client: TestClient):
        # 1. Launch a sandbox
        launch_payload = {
            "templateId": "python-dev-v2",
            "agentName": "test-backend-agent",
            "timeoutSeconds": 600,
            "envOverrides": {"TEST_ENV_KEY": "test_env_val"},
        }
        with patch(
            "image_registry_router.fuzekeys_resolver.resolve_secrets",
            new_callable=AsyncMock,
            return_value={
                "ANTHROPIC_API_KEY": "sk-mock-key-123",
                "DATABASE_URL": "postgresql://mock:5432/test",
            },
        ):
            launch_res = client.post("/api/sandboxes/launch", json=launch_payload)
            assert launch_res.status_code == 200
            launch_data = launch_res.json()
            assert launch_data["status"] == "launched"

            sbx = launch_data["sandbox"]
            assert sbx["name"] == "test-backend-agent"
            assert sbx["templateId"] == "python-dev-v2"
            assert sbx["status"] == "running"
            assert sbx["podName"].startswith("agent-sbx-python-dev")
            assert sbx["secretName"] is not None
            assert sbx["networkPolicyName"] is not None
            assert sbx["networkIsolation"] == "outbound-only"
            assert any("[SECRETS]" in log for log in sbx["logs"])
            assert any("[NETPOL]" in log for log in sbx["logs"])

            sbx_id = sbx["id"]

        # 2. Verify sandbox listed in /api/sandboxes
        list_res = client.get("/api/sandboxes")
        assert list_res.status_code == 200
        sandboxes = list_res.json()
        assert any(s["id"] == sbx_id for s in sandboxes)

        # 3. Terminate sandbox
        term_res = client.post(f"/api/sandboxes/{sbx_id}/terminate")
        assert term_res.status_code == 200
        term_data = term_res.json()
        assert term_data["status"] == "terminated"
        assert term_data["sandboxId"] == sbx_id

        # 4. Verify termination reflected
        list_res_after = client.get("/api/sandboxes")
        updated_sbx = next(
            (s for s in list_res_after.json() if s["id"] == sbx_id), None
        )
        assert updated_sbx is not None
        assert updated_sbx["status"] == "terminated"

    def test_terminate_unknown_sandbox_returns_404(self, client: TestClient):
        response = client.post("/api/sandboxes/unknown-sbx-id/terminate")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test Suite 4: WebSocket Multi-Agent Streaming
# ---------------------------------------------------------------------------
class TestMultiAgentWebSocketStreaming:
    """Tests real-time communication via /api/ws/multi-agent."""

    def test_websocket_ping_pong(self, client: TestClient):
        with client.websocket_connect("/api/ws/multi-agent") as ws:
            init_msg = ws.receive_json()
            assert init_msg.get("type") == "connection_established"

            ws.send_json({"action": "ping"})
            resp = ws.receive_json()
            assert resp.get("type") == "pong"

    def test_websocket_chat_streaming(self, client: TestClient):
        with patch(
            "image_registry_router.brain_store.search",
            new_callable=AsyncMock,
            return_value=[
                {
                    "id": "doc-1",
                    "title": "Architecture Guidelines",
                    "content": "Follow PEP8 and modular component layout.",
                    "score": 0.95,
                }
            ],
        ):
            with client.websocket_connect("/api/ws/multi-agent") as ws:
                init_msg = ws.receive_json()
                assert init_msg.get("type") == "connection_established"

                ws.send_json(
                    {
                        "action": "chat",
                        "agentId": "python-dev",
                        "message": "Hello agent, analyze this test case",
                    }
                )

                # Receive status and thought events
                status_msg = ws.receive_json()
                assert status_msg.get("type") == "agent_status"
                assert status_msg.get("status") == "executing"

                thought_msg = ws.receive_json()
                assert thought_msg.get("type") == "agent_thought"

                # Receive stream chunks and completion
                received_types = set()
                for _ in range(30):
                    msg = ws.receive_json()
                    msg_type = msg.get("type")
                    received_types.add(msg_type)
                    if msg_type == "agent_message" or msg.get("isFinal") is True:
                        break

                assert "agent_chunk" in received_types
                assert "agent_message" in received_types

    def test_agent_relay_pod_connection_and_forwarding(self, client: TestClient):
        with client.websocket_connect("/api/ws/agent-relay/test-agent-pod") as pod_ws:
            pod_ws.send_json(
                {
                    "agentId": "test-agent-pod",
                    "type": "agent_status",
                    "status": "online",
                    "currentTask": "Pod runner initialized",
                }
            )

            with client.websocket_connect("/api/ws/multi-agent") as chat_ws:
                init_msg = chat_ws.receive_json()
                assert init_msg.get("type") == "connection_established"

                pod_ws.send_json(
                    {
                        "agentId": "test-agent-pod",
                        "type": "agent_chunk",
                        "chunk": "Echo from sandbox pod container",
                        "isFinal": False,
                    }
                )
                received = chat_ws.receive_json()
                assert received.get("type") == "agent_chunk"
                assert received.get("chunk") == "Echo from sandbox pod container"
