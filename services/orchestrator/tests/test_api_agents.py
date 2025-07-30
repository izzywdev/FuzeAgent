"""
Test cases for Agents API endpoints
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
@pytest.mark.database
class TestAgentsAPI:
    """Test Agent API endpoints"""
    
    @pytest.fixture
    def setup_org_and_team(self, client: TestClient):
        """Setup organization and team for agent tests"""
        # Create organization
        org_data = {
            "name": "Test Organization",
            "description": "For agent testing"
        }
        org_response = client.post("/organizations", json=org_data)
        org_id = org_response.json()["id"]
        
        # Create team
        team_data = {
            "organization_id": org_id,
            "name": "Development Team",
            "description": "Test team",
            "team_type": "development"
        }
        team_response = client.post("/teams", json=team_data)
        team_id = team_response.json()["id"]
        
        return {"org_id": org_id, "team_id": team_id}
    
    def test_get_agents_empty(self, client: TestClient):
        """Test getting agents when none exist"""
        response = client.get("/agents")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_create_custom_agent(self, client: TestClient, setup_org_and_team):
        """Test creating a custom agent"""
        team_id = setup_org_and_team["team_id"]
        
        agent_data = {
            "team_id": team_id,
            "name": "Test Agent",
            "role": "Python Developer",
            "type": "python_developer",
            "config": {
                "goal": "Develop Python applications",
                "backstory": "Expert developer",
                "tools": ["code_generation"],
                "skills": ["python", "fastapi"]
            }
        }
        
        response = client.post("/agents", json=agent_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == agent_data["name"]
        assert data["role"] == agent_data["role"]
        assert data["team_id"] == team_id
        assert "id" in data
    
    def test_create_agent_from_template(self, client: TestClient, setup_org_and_team):
        """Test creating agent from template"""
        team_id = setup_org_and_team["team_id"]
        
        template_data = {
            "template_id": "python_developer",
            "overrides": {
                "team_id": team_id,
                "name": "Python Expert",
                "goal": "Build amazing Python applications"
            }
        }
        
        response = client.post("/agents/from-template", json=template_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == template_data["overrides"]["name"]
        assert data["template_id"] == template_data["template_id"]
        assert data["team_id"] == team_id
    
    def test_create_agent_from_template_invalid_template(self, client: TestClient, setup_org_and_team):
        """Test creating agent from non-existent template"""
        team_id = setup_org_and_team["team_id"]
        
        template_data = {
            "template_id": "non_existent_template",
            "overrides": {
                "team_id": team_id,
                "name": "Test Agent"
            }
        }
        
        response = client.post("/agents/from-template", json=template_data)
        assert response.status_code == 404
    
    def test_create_agent_invalid_team(self, client: TestClient):
        """Test creating agent with invalid team ID"""
        fake_team_id = "550e8400-e29b-41d4-a716-446655440999"
        
        agent_data = {
            "team_id": fake_team_id,
            "name": "Test Agent",
            "role": "Developer",
            "type": "python_developer",
            "config": {}
        }
        
        response = client.post("/agents", json=agent_data)
        assert response.status_code == 404
    
    def test_get_agent_by_id(self, client: TestClient, setup_org_and_team):
        """Test getting agent by ID"""
        team_id = setup_org_and_team["team_id"]
        
        # Create agent
        agent_data = {
            "team_id": team_id,
            "name": "Test Agent",
            "role": "Developer",
            "type": "python_developer",
            "config": {"goal": "Test goal"}
        }
        create_response = client.post("/agents", json=agent_data)
        agent_id = create_response.json()["id"]
        
        # Get agent
        response = client.get(f"/agents/{agent_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == agent_id
        assert data["name"] == agent_data["name"]
    
    def test_get_agent_not_found(self, client: TestClient):
        """Test getting non-existent agent"""
        fake_id = "550e8400-e29b-41d4-a716-446655440999"
        response = client.get(f"/agents/{fake_id}")
        assert response.status_code == 404
    
    def test_get_agents_filtered_by_team(self, client: TestClient, setup_org_and_team):
        """Test getting agents filtered by team"""
        team_id = setup_org_and_team["team_id"]
        
        # Create agent in the team
        agent_data = {
            "team_id": team_id,
            "name": "Team Agent",
            "role": "Developer",
            "type": "python_developer",
            "config": {}
        }
        client.post("/agents", json=agent_data)
        
        # Get agents filtered by team
        response = client.get(f"/agents?team_id={team_id}")
        assert response.status_code == 200
        
        agents = response.json()
        assert len(agents) == 1
        assert agents[0]["team_id"] == team_id
    
    def test_assign_task_to_agent(self, client: TestClient, setup_org_and_team):
        """Test assigning task to agent"""
        team_id = setup_org_and_team["team_id"]
        
        # Create agent
        agent_data = {
            "team_id": team_id,
            "name": "Task Agent",
            "role": "Developer",
            "type": "python_developer",
            "config": {}
        }
        create_response = client.post("/agents", json=agent_data)
        agent_id = create_response.json()["id"]
        
        # Assign task
        task_data = {
            "title": "Test Task",
            "description": "A test task for the agent",
            "created_by": "test-user"
        }
        
        response = client.post(f"/agents/{agent_id}/tasks", json=task_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "task_id" in data
        assert data["message"] == "Task assigned successfully"
    
    def test_assign_task_to_nonexistent_agent(self, client: TestClient):
        """Test assigning task to non-existent agent"""
        fake_agent_id = "550e8400-e29b-41d4-a716-446655440999"
        
        task_data = {
            "title": "Test Task",
            "description": "A test task",
            "created_by": "test-user"
        }
        
        response = client.post(f"/agents/{fake_agent_id}/tasks", json=task_data)
        assert response.status_code == 404