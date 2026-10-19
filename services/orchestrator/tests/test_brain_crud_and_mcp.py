import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

import sys
import os

# Ensure paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../mcp-servers/fuzeagent-server")))

import brain_store
from image_registry_router import router as image_registry_router, brain_router
from mcp_integration import FuzeAgentMCPServer as InOrchestratorMCPServer
from server import FuzeAgentMCPServer as StandaloneMCPServer
from fastapi import FastAPI


@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(image_registry_router)
    app.include_router(brain_router)
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


# ---------------------------------------------------------------------------
# 1. Brain Store Unit Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_brain_store_seeded_brains():
    brains = await brain_store.list_brains()
    assert len(brains) >= 7
    ids = [b["id"] for b in brains]
    assert "brain_org_global" in ids
    assert "brain_cross_frontend" in ids
    assert "brain_cross_devops" in ids
    assert "brain_cross_backend" in ids
    assert "brain_team_platform" in ids
    assert "brain_agent_python_dev" in ids
    assert "brain_agent_react_dev" in ids


@pytest.mark.asyncio
async def test_brain_store_filtering():
    # Filter by cross_functional
    cf_brains = await brain_store.list_brains(scope="cross_functional")
    assert len(cf_brains) >= 3
    domains = [b["functional_domain"] for b in cf_brains]
    assert "frontend" in domains
    assert "devops" in domains
    assert "backend" in domains

    # Filter by specific domain
    fe_brains = await brain_store.list_brains(functional_domain="frontend")
    assert any(b["id"] == "brain_cross_frontend" for b in fe_brains)


@pytest.mark.asyncio
async def test_brain_store_crud():
    # Create
    new_brain = await brain_store.create_brain({
        "id": "brain_test_qa",
        "name": "QA Testing Brain",
        "description": "Quality assurance strategies and Playwright tests",
        "scope": "cross_functional",
        "functional_domain": "qa",
        "tags": ["qa", "testing", "automation"],
    })
    assert new_brain["id"] == "brain_test_qa"
    assert new_brain["functional_domain"] == "qa"

    # Get
    fetched = await brain_store.get_brain("brain_test_qa")
    assert fetched is not None
    assert fetched["name"] == "QA Testing Brain"

    # Update
    updated = await brain_store.update_brain("brain_test_qa", {
        "description": "Updated QA strategies with AI vision checks",
        "tags": ["qa", "testing", "ai-vision"],
    })
    assert "ai-vision" in updated["tags"]
    assert "Updated QA strategies" in updated["description"]

    # Associate
    assoc = await brain_store.associate_brain("brain_test_qa", {
        "scope": "team",
        "team_id": "team_qa_core",
    })
    assert assoc["scope"] == "team"
    assert assoc["team_id"] == "team_qa_core"

    # Delete
    deleted = await brain_store.delete_brain("brain_test_qa")
    assert deleted is True
    assert await brain_store.get_brain("brain_test_qa") is None


@pytest.mark.asyncio
async def test_brain_store_agent_hierarchy_resolution():
    # React dev resolution
    react_res = await brain_store.get_agent_brains(agent_id="react-dev")
    assert react_res["agent_id"] == "react-dev"
    assert react_res["functional_domain"] == "frontend"
    brain_ids = [b["id"] for b in react_res["brains"]]
    assert "brain_agent_react_dev" in brain_ids
    assert "brain_cross_frontend" in brain_ids
    assert "brain_org_global" in brain_ids

    # DevOps agent resolution
    devops_res = await brain_store.get_agent_brains(agent_id="devops-lead")
    assert devops_res["functional_domain"] == "devops"
    devops_ids = [b["id"] for b in devops_res["brains"]]
    assert "brain_cross_devops" in devops_ids
    assert "brain_org_global" in devops_ids


# ---------------------------------------------------------------------------
# 2. REST API Endpoint Tests
# ---------------------------------------------------------------------------

def test_rest_list_brains(client):
    # Test /brains
    res = client.get("/brains")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 7

    # Test /api/brains
    res_api = client.get("/api/brains?scope=cross_functional")
    assert res_api.status_code == 200
    cf_data = res_api.json()
    assert all(b["scope"] == "cross_functional" for b in cf_data)


def test_rest_brain_crud_lifecycle(client):
    brain_payload = {
        "id": "brain_rest_security",
        "name": "AppSec & Vulnerability Management Brain",
        "description": "CVE analysis, container hardening, and secret rotation guidelines",
        "organization_id": "org_default",
        "scope": "cross_functional",
        "functional_domain": "security",
        "tags": ["security", "cve", "hardening"],
        "metadata": {"compliance": "SOC2"},
    }

    # POST /brains
    create_res = client.post("/brains", json=brain_payload)
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["id"] == "brain_rest_security"

    # GET /brains/{id}
    get_res = client.get("/brains/brain_rest_security")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "AppSec & Vulnerability Management Brain"

    # PUT /brains/{id}
    put_res = client.put("/brains/brain_rest_security", json={
        "description": "Hardened container CVE scanning and FuzeKeys rotation",
        "tags": ["security", "cve", "fuzekeys"],
    })
    assert put_res.status_code == 200
    assert "fuzekeys" in put_res.json()["tags"]

    # POST /brains/{id}/associate
    assoc_res = client.post("/brains/brain_rest_security/associate", json={
        "scope": "team",
        "team_id": "team_security_secops",
    })
    assert assoc_res.status_code == 200
    assert assoc_res.json()["scope"] == "team"
    assert assoc_res.json()["team_id"] == "team_security_secops"

    # DELETE /brains/{id}
    del_res = client.delete("/brains/brain_rest_security")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify 404
    get_again = client.get("/brains/brain_rest_security")
    assert get_again.status_code == 404


def test_rest_agent_brains_resolution(client):
    # GET /agents/{agent_id}/brains
    res = client.get("/agents/react-dev/brains")
    assert res.status_code == 200
    body = res.json()
    assert body["agent_id"] == "react-dev"
    assert body["functional_domain"] == "frontend"
    assert len(body["brains"]) >= 3
    tiers = [h["tier"] for h in body["hierarchy"]]
    assert 1 in tiers  # Persona tier
    assert 3 in tiers  # Cross-functional tier
    assert 4 in tiers  # Organization tier


# ---------------------------------------------------------------------------
# 3. MCP Server Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_standalone_mcp_server_brain_tools():
    mcp_server = StandaloneMCPServer("http://localhost:8000")

    # Simulate tool call directly
    list_result = await mcp_server._list_brains({"scope": "cross_functional"})
    assert list_result.content
    assert "Cross-Functional" in list_result.content[0].text

    agent_result = await mcp_server._get_agent_brains({"agent_id": "react-dev"})
    assert agent_result.content
    assert "react-dev" in agent_result.content[0].text
    assert "CROSS_FUNCTIONAL BRAIN" in agent_result.content[0].text

    get_result = await mcp_server._get_brain("brain_cross_devops")
    assert get_result.content
    assert "Cross-Functional DevOps & SRE Brain" in get_result.content[0].text


@pytest.mark.asyncio
async def test_in_orchestrator_mcp_server():
    in_mcp = InOrchestratorMCPServer()
    
    # Verify tools defined
    tool_names = [t.name for t in in_mcp.tools]
    assert "list_brains" in tool_names
    assert "get_brain" in tool_names
    assert "create_brain" in tool_names
    assert "update_brain" in tool_names
    assert "delete_brain" in tool_names
    assert "associate_brain" in tool_names
    assert "get_agent_brains" in tool_names

    # Verify resources defined
    resource_uris = [r.uri for r in in_mcp.resources]
    assert "fuzeagent://brains" in resource_uris

    # Test tool call
    res = await in_mcp.handle_tool_call("list_brains", {"functional_domain": "frontend"})
    assert "brains" in res
    assert any(b["id"] == "brain_cross_frontend" for b in res["brains"])

    # Test agent brains resolution tool call
    agent_res = await in_mcp.handle_tool_call("get_agent_brains", {"agent_id": "react-dev"})
    assert agent_res["agent_id"] == "react-dev"
    assert len(agent_res["brains"]) >= 3

    # Test resource request
    resource_data = await in_mcp.handle_resource_request("fuzeagent://brains")
    assert "brains" in resource_data
    assert len(resource_data["brains"]) >= 7

    brain_res = await in_mcp.handle_resource_request("fuzeagent://brains/brain_cross_devops")
    assert "brain" in brain_res
    assert brain_res["brain"]["functional_domain"] == "devops"
