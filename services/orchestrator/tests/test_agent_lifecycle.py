"""
Unit & Integration Tests for Agent Lifecycle REST API & Streaming Session Management.
Tests:
A. List available agent templates (GET /agent-templates, GET /api/agent-templates, GET /templates)
B. Create custom agent template (POST /agent-templates, POST /api/agent-templates)
C. Create agent from template (POST /agents, POST /api/agents, POST /agents/from-template)
D. List agents (GET /agents, GET /api/agents)
E. Start agent session with bidirectional in/out streaming wiring (POST /agents/{agent_id}/sessions, WebSocket, SSE)
F. Terminate an agent session (DELETE /sessions/{session_id}, POST /sessions/{session_id}/terminate)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_lifecycle_router import router as lifecycle_router


@pytest.fixture
def app():
    test_app = FastAPI(title="Agent Lifecycle Test API")
    test_app.include_router(lifecycle_router)
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Requirement A: List Agent Templates
# ---------------------------------------------------------------------------
class TestListAgentTemplates:
    """Tests Requirement A: List agent templates using REST API."""

    def test_list_templates_root(self, client):
        res = client.get("/agent-templates")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 5
        template_ids = {t["id"] for t in data}
        assert "python_developer" in template_ids
        assert "react_developer" in template_ids
        assert "typescript_developer" in template_ids

        # Check template structure
        python_tmpl = next(t for t in data if t["id"] == "python_developer")
        assert python_tmpl["name"] == "Python Developer"
        assert python_tmpl["category"] == "development"
        assert "tools" in python_tmpl
        assert "skills" in python_tmpl
        assert "code_generation" in python_tmpl["tools"]
        assert "python" in python_tmpl["skills"]
        assert "config" in python_tmpl
        assert "image" in python_tmpl

    def test_list_templates_api_prefix(self, client):
        res = client.get("/api/agent-templates")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert any(t["id"] == "python_developer" for t in data)

    def test_list_templates_alias(self, client):
        res = client.get("/templates")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_list_templates_filter_category(self, client):
        res = client.get("/agent-templates?category=development")
        assert res.status_code == 200
        data = res.json()
        for t in data:
            assert t["category"] == "development"

    def test_get_single_template(self, client):
        res = client.get("/agent-templates/python_developer")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "python_developer"
        assert data["name"] == "Python Developer"

    def test_get_single_template_not_found(self, client):
        res = client.get("/agent-templates/non_existent_template_xyz")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Requirement B: Create an Agent Template
# ---------------------------------------------------------------------------
class TestCreateAgentTemplate:
    """Tests Requirement B: Create an agent template."""

    def test_create_custom_template_success(self, client):
        payload = {
            "id": "security_auditor_v1",
            "name": "Security Auditor",
            "category": "quality_assurance",
            "role": "Lead Security Auditor",
            "description": "Specialized in SAST and vulnerability analysis",
            "system_prompt": "You are a specialized security auditor verifying CVEs.",
            "default_goal": "Audit repositories for high and critical CVEs",
            "default_backstory": "Veteran cybersecurity engineer with 10+ years experience",
            "tools": ["security_audit", "vulnerability_scanning", "sbom_analyzer"],
            "skills": ["sast", "cve_analysis", "owasp"],
            "default_model": "claude-sonnet-4-20250514",
            "default_temperature": 0.2,
            "image": "ghcr.io/izzywdev/fuzeagent/claude-runner-qa:latest",
        }

        res = client.post("/agent-templates", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] == "security_auditor_v1"
        assert data["name"] == "Security Auditor"
        assert data["category"] == "quality_assurance"
        assert data["tools"] == payload["tools"]
        assert data["skills"] == payload["skills"]
        assert data["image"] == payload["image"]

        # Verify it now appears in the list
        list_res = client.get("/agent-templates")
        assert list_res.status_code == 200
        all_ids = [t["id"] for t in list_res.json()]
        assert "security_auditor_v1" in all_ids

        # Verify get by ID
        get_res = client.get("/agent-templates/security_auditor_v1")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "Security Auditor"

    def test_create_template_api_prefix(self, client):
        payload = {
            "name": "DevOps SRE Lead",
            "category": "devops",
            "description": "Kubernetes and infrastructure reliability engineer",
            "tools": ["k8s_inspect", "helm_diff"],
        }
        res = client.post("/api/agent-templates", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        assert data["name"] == "DevOps SRE Lead"


# ---------------------------------------------------------------------------
# Requirement C: Create an Agent from a Template
# ---------------------------------------------------------------------------
class TestCreateAgentFromTemplate:
    """Tests Requirement C: Create an agent from a template."""

    def test_create_agent_from_template_happy_path(self, client):
        payload = {
            "template_id": "python_developer",
            "name": "Production PyBot Alpha",
            "role": "Senior Backend Architect",
            "overrides": {
                "goal": "Build highly scalable async FastAPI microservices",
                "temperature": 0.4,
                "model": "claude-3-5-sonnet-20241022",
            },
            "repository_settings": {
                "repository_url": "https://github.com/izzywdev/FuzeAgent.git",
                "branch": "main",
            },
        }

        res = client.post("/agents", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        assert data["agent_id"] == data["id"]
        assert data["name"] == "Production PyBot Alpha"
        assert data["role"] == "Senior Backend Architect"
        assert data["status"] == "active"
        assert data["template_id"] == "python_developer"
        assert (
            data["config"]["goal"]
            == "Build highly scalable async FastAPI microservices"
        )
        assert data["config"]["temperature"] == 0.4

    def test_create_agent_via_api_prefix(self, client):
        payload = {
            "templateId": "react_developer",
            "name": "Frontend Designer Agent",
        }
        res = client.post("/api/agents", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Frontend Designer Agent"
        assert data["template_id"] == "react_developer"

    def test_create_agent_legacy_path(self, client):
        payload = {
            "template_id": "typescript_developer",
            "name": "TS Core Runner",
        }
        res = client.post("/agents/from-template", json=payload)
        assert res.status_code == 201
        assert res.json()["name"] == "TS Core Runner"

    def test_create_agent_invalid_template(self, client):
        payload = {
            "template_id": "non_existent_fake_template",
            "name": "Invalid Agent",
        }
        res = client.post("/agents", json=payload)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Requirement D: List Agents
# ---------------------------------------------------------------------------
class TestListAgents:
    """Tests Requirement D: List agents."""

    def test_list_agents_contains_created_agents(self, client):
        # Create an agent
        create_res = client.post(
            "/agents",
            json={
                "template_id": "devops_engineer",
                "name": "Cluster Operator Bot",
            },
        )
        assert create_res.status_code == 201
        agent_id = create_res.json()["id"]

        # List agents
        list_res = client.get("/agents")
        assert list_res.status_code == 200
        agents = list_res.json()
        assert isinstance(agents, list)
        matching = [
            a for a in agents if a["id"] == agent_id or a.get("agent_id") == agent_id
        ]
        assert len(matching) == 1
        assert matching[0]["name"] == "Cluster Operator Bot"

    def test_list_agents_api_prefix(self, client):
        res = client.get("/api/agents")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_get_single_agent_by_id(self, client):
        create_res = client.post(
            "/agents",
            json={
                "template_id": "qa_engineer",
                "name": "QA Verifier 1",
            },
        )
        agent_id = create_res.json()["id"]

        get_res = client.get(f"/agents/{agent_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == agent_id
        assert get_res.json()["name"] == "QA Verifier 1"

    def test_get_non_existent_agent(self, client):
        res = client.get("/agents/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Requirement E: Start Agent Session & In/Out Streaming Wiring
# ---------------------------------------------------------------------------
class TestAgentSessionAndStreaming:
    """Tests Requirement E: Start agent session including wiring in/out streaming."""

    def test_start_session_endpoint(self, client):
        # 1. Create agent
        agent_res = client.post(
            "/agents",
            json={"template_id": "python_developer", "name": "Streaming Python Bot"},
        )
        agent_id = agent_res.json()["id"]

        # 2. Start session
        session_res = client.post(
            f"/agents/{agent_id}/sessions",
            json={"session_name": "API Testing Session"},
        )
        assert session_res.status_code == 201
        session = session_res.json()

        assert "session_id" in session
        assert session["session_id"].startswith("session-")
        assert session["status"] == "active"
        assert session["agent_id"] == agent_id

        # Verify streaming endpoints are wired and returned
        streaming = session["streaming"]
        assert "websocket_url" in streaming
        assert "stream_url" in streaming
        assert "messages_url" in streaming
        assert session["session_id"] in streaming["websocket_url"]
        assert session["session_id"] in streaming["stream_url"]

        # 3. Retrieve session details
        get_session_res = client.get(f"/sessions/{session['session_id']}")
        assert get_session_res.status_code == 200
        assert get_session_res.json()["status"] == "active"

    def test_start_session_root_post(self, client):
        session_res = client.post(
            "/sessions",
            json={"agent_id": "python-dev", "session_name": "Direct Session"},
        )
        assert session_res.status_code == 201
        assert session_res.json()["status"] == "active"

    def test_websocket_chat_streaming(self, client):
        # Start a session
        session_res = client.post(
            "/sessions",
            json={"agent_id": "python-dev", "session_name": "WS Test"},
        )
        session_id = session_res.json()["session_id"]

        # Connect WebSocket to the wired session endpoint
        with client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
            # First message received is session_connected
            init_msg = ws.receive_json()
            assert init_msg["type"] == "session_connected"
            assert init_msg["sessionId"] == session_id

            # Send prompt over WebSocket
            ws.send_json({"action": "chat", "message": "What is the time now in LA?"})

            # Receive status update
            status_msg = ws.receive_json()
            assert status_msg["type"] == "agent_status"
            assert status_msg["status"] == "executing"

            # Receive thought update
            thought_msg = ws.receive_json()
            assert thought_msg["type"] == "agent_thought"

            # Collect streaming chunks
            received_chunks = []
            final_message = None

            while True:
                chunk_msg = ws.receive_json()
                if chunk_msg["type"] == "agent_chunk":
                    received_chunks.append(chunk_msg["chunk"])
                elif chunk_msg["type"] == "agent_message":
                    final_message = chunk_msg
                    break

            assert len(received_chunks) > 0
            assert final_message is not None
            assert final_message["isFinal"] is True
            assert "Los Angeles" in final_message["content"]

    def test_post_message_and_sse_stream(self, client):
        session_res = client.post("/sessions", json={"agent_id": "python-dev"})
        session_id = session_res.json()["session_id"]

        # Post message to session
        post_res = client.post(
            f"/sessions/{session_id}/messages",
            json={"message": "Compute status check"},
        )
        assert post_res.status_code == 200
        assert post_res.json()["status"] == "processing"


# ---------------------------------------------------------------------------
# Requirement F: Terminate Session
# ---------------------------------------------------------------------------
class TestTerminateSession:
    """Tests Requirement F: Terminate session."""

    def test_terminate_session_delete(self, client):
        # Create session
        session_res = client.post("/sessions", json={"agent_id": "python-dev"})
        session_id = session_res.json()["session_id"]

        # Terminate via DELETE
        del_res = client.delete(f"/sessions/{session_id}")
        assert del_res.status_code == 200
        data = del_res.json()
        assert data["session_id"] == session_id
        assert data["status"] == "terminated"
        assert "terminated_at" in data

        # Check session status is now terminated
        get_res = client.get(f"/sessions/{session_id}")
        assert get_res.status_code == 200
        assert get_res.json()["status"] == "terminated"

        # Posting messages to terminated session is rejected with 400
        post_res = client.post(
            f"/sessions/{session_id}/messages",
            json={"message": "Should fail"},
        )
        assert post_res.status_code == 400
        assert "terminated" in post_res.json()["detail"].lower()

    def test_terminate_session_post_alias(self, client):
        session_res = client.post("/sessions", json={"agent_id": "python-dev"})
        session_id = session_res.json()["session_id"]

        term_res = client.post(f"/api/sessions/{session_id}/terminate")
        assert term_res.status_code == 200
        assert term_res.json()["status"] == "terminated"

    def test_terminate_non_existent_session(self, client):
        res = client.delete("/sessions/session-fake-id-123")
        assert res.status_code == 404
