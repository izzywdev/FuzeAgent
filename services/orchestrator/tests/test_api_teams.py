"""
Test cases for Teams API endpoints
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
@pytest.mark.database
class TestTeamsAPI:
    """Test Team API endpoints"""

    @pytest.fixture
    def setup_organization(self, client: TestClient):
        """Setup organization for team tests"""
        org_data = {"name": "Test Organization", "description": "For team testing"}
        response = client.post("/organizations", json=org_data)
        return response.json()["id"]

    def test_get_teams_empty(self, client: TestClient):
        """Test getting teams when none exist"""
        response = client.get("/teams")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_team(self, client: TestClient, setup_organization):
        """Test creating a new team"""
        org_id = setup_organization

        team_data = {
            "organization_id": org_id,
            "name": "Development Team",
            "description": "A development team",
            "team_type": "development",
            "settings": {"max_agents": 10},
        }

        response = client.post("/teams", json=team_data)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == team_data["name"]
        assert data["description"] == team_data["description"]
        assert data["organization_id"] == org_id
        assert data["team_type"] == team_data["team_type"]
        assert "id" in data
        assert "created_at" in data

    def test_create_team_missing_fields(self, client: TestClient):
        """Test creating team with missing required fields"""
        team_data = {"description": "Missing name and org"}

        response = client.post("/teams", json=team_data)
        assert response.status_code == 422  # Validation error

    def test_create_team_invalid_organization(self, client: TestClient):
        """Test creating team with invalid organization ID"""
        fake_org_id = "550e8400-e29b-41d4-a716-446655440999"

        team_data = {
            "organization_id": fake_org_id,
            "name": "Test Team",
            "description": "Test description",
            "team_type": "development",
        }

        response = client.post("/teams", json=team_data)
        assert response.status_code == 404

    def test_get_team_by_id(self, client: TestClient, setup_organization):
        """Test getting team by ID"""
        org_id = setup_organization

        # Create team
        team_data = {
            "organization_id": org_id,
            "name": "Test Team",
            "description": "Test description",
            "team_type": "development",
        }
        create_response = client.post("/teams", json=team_data)
        team_id = create_response.json()["id"]

        # Get team
        response = client.get(f"/teams/{team_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == team_id
        assert data["name"] == team_data["name"]

    def test_get_team_not_found(self, client: TestClient):
        """Test getting non-existent team"""
        fake_id = "550e8400-e29b-41d4-a716-446655440999"
        response = client.get(f"/teams/{fake_id}")
        assert response.status_code == 404

    def test_get_teams_filtered_by_organization(
        self, client: TestClient, setup_organization
    ):
        """Test getting teams filtered by organization"""
        org_id = setup_organization

        # Create team in the organization
        team_data = {
            "organization_id": org_id,
            "name": "Org Team",
            "description": "Team in organization",
            "team_type": "development",
        }
        client.post("/teams", json=team_data)

        # Get teams filtered by organization
        response = client.get(f"/teams?organization_id={org_id}")
        assert response.status_code == 200

        teams = response.json()
        assert len(teams) == 1
        assert teams[0]["organization_id"] == org_id

    def test_update_team(self, client: TestClient, setup_organization):
        """Test updating team"""
        org_id = setup_organization

        # Create team
        team_data = {
            "organization_id": org_id,
            "name": "Original Team",
            "description": "Original description",
            "team_type": "development",
        }
        create_response = client.post("/teams", json=team_data)
        team_id = create_response.json()["id"]

        # Update team
        update_data = {
            "name": "Updated Team",
            "description": "Updated description",
            "team_type": "operations",
        }
        response = client.put(f"/teams/{team_id}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["team_type"] == update_data["team_type"]

    def test_update_team_not_found(self, client: TestClient):
        """Test updating non-existent team"""
        fake_id = "550e8400-e29b-41d4-a716-446655440999"
        update_data = {"name": "Updated Name"}

        response = client.put(f"/teams/{fake_id}", json=update_data)
        assert response.status_code == 404

    def test_delete_team(self, client: TestClient, setup_organization):
        """Test deleting team"""
        org_id = setup_organization

        # Create team
        team_data = {
            "organization_id": org_id,
            "name": "To Be Deleted",
            "description": "This will be deleted",
            "team_type": "development",
        }
        create_response = client.post("/teams", json=team_data)
        team_id = create_response.json()["id"]

        # Delete team
        response = client.delete(f"/teams/{team_id}")
        assert response.status_code == 200
        assert "message" in response.json()

        # Verify deletion
        get_response = client.get(f"/teams/{team_id}")
        assert get_response.status_code == 404

    def test_delete_team_not_found(self, client: TestClient):
        """Test deleting non-existent team"""
        fake_id = "550e8400-e29b-41d4-a716-446655440999"

        response = client.delete(f"/teams/{fake_id}")
        assert response.status_code == 404

    def test_get_team_agents(self, client: TestClient, setup_organization):
        """Test getting agents in a team"""
        org_id = setup_organization

        # Create team
        team_data = {
            "organization_id": org_id,
            "name": "Agent Team",
            "description": "Team for agent testing",
            "team_type": "development",
        }
        create_response = client.post("/teams", json=team_data)
        team_id = create_response.json()["id"]

        # Create agent in team
        agent_data = {
            "team_id": team_id,
            "name": "Team Agent",
            "role": "Developer",
            "type": "python_developer",
            "config": {},
        }
        client.post("/agents", json=agent_data)

        # Get team agents
        response = client.get(f"/teams/{team_id}/agents")
        assert response.status_code == 200

        agents = response.json()
        assert len(agents) == 1
        assert agents[0]["team_id"] == team_id

    def test_create_team_with_different_types(
        self, client: TestClient, setup_organization
    ):
        """Test creating teams with different team types"""
        org_id = setup_organization

        team_types = ["development", "operations", "research", "qa", "marketing"]
        created_teams = []

        for team_type in team_types:
            team_data = {
                "organization_id": org_id,
                "name": f"{team_type.title()} Team",
                "description": f"Team for {team_type} activities",
                "team_type": team_type,
                "settings": {"department": team_type},
            }

            response = client.post("/teams", json=team_data)
            assert response.status_code == 201

            data = response.json()
            assert data["team_type"] == team_type
            assert data["settings"]["department"] == team_type
            created_teams.append(data["id"])

        # Verify all teams exist
        response = client.get(f"/teams?organization_id={org_id}")
        assert response.status_code == 200

        teams = response.json()
        assert len(teams) == len(team_types)

    def test_create_team_with_complex_settings(
        self, client: TestClient, setup_organization
    ):
        """Test creating team with complex settings"""
        org_id = setup_organization

        team_data = {
            "organization_id": org_id,
            "name": "Advanced Development Team",
            "description": "High-performance development team",
            "team_type": "development",
            "settings": {
                "max_agents": 15,
                "working_hours": {"start": "09:00", "end": "17:00", "timezone": "UTC"},
                "skills": ["python", "javascript", "docker", "kubernetes"],
                "methodologies": ["agile", "scrum"],
                "tools": {
                    "version_control": "git",
                    "ci_cd": "github_actions",
                    "monitoring": "datadog",
                },
            },
        }

        response = client.post("/teams", json=team_data)
        assert response.status_code == 201

        data = response.json()
        assert data["settings"]["max_agents"] == 15
        assert "python" in data["settings"]["skills"]
        assert data["settings"]["tools"]["version_control"] == "git"

    def test_team_organization_cascade_delete(
        self, client: TestClient, setup_organization
    ):
        """Test team behavior when organization is deleted"""
        org_id = setup_organization

        # Create team
        team_data = {
            "organization_id": org_id,
            "name": "Test Team",
            "description": "Team to test cascade",
            "team_type": "development",
        }
        team_response = client.post("/teams", json=team_data)
        team_id = team_response.json()["id"]

        # Verify team exists
        response = client.get(f"/teams/{team_id}")
        assert response.status_code == 200

        # Delete organization
        client.delete(f"/organizations/{org_id}")

        # Team should still exist but be orphaned (depending on business logic)
        # This test documents current behavior
        response = client.get(f"/teams/{team_id}")
        # Could be 200 (orphaned) or 404 (cascade deleted) depending on implementation
        assert response.status_code in [200, 404]

    def test_create_multiple_teams_same_name_different_orgs(self, client: TestClient):
        """Test creating teams with same name in different organizations"""
        # Create two organizations
        org1_data = {"name": "Organization 1", "description": "First org"}
        org1_response = client.post("/organizations", json=org1_data)
        org1_id = org1_response.json()["id"]

        org2_data = {"name": "Organization 2", "description": "Second org"}
        org2_response = client.post("/organizations", json=org2_data)
        org2_id = org2_response.json()["id"]

        # Create teams with same name in different organizations
        team_name = "Development Team"

        team1_data = {
            "organization_id": org1_id,
            "name": team_name,
            "description": "Team in org 1",
            "team_type": "development",
        }
        team1_response = client.post("/teams", json=team1_data)
        assert team1_response.status_code == 201

        team2_data = {
            "organization_id": org2_id,
            "name": team_name,
            "description": "Team in org 2",
            "team_type": "development",
        }
        team2_response = client.post("/teams", json=team2_data)
        assert team2_response.status_code == 201

        # Both teams should exist with same name but different IDs
        team1_id = team1_response.json()["id"]
        team2_id = team2_response.json()["id"]
        assert team1_id != team2_id
        assert team1_response.json()["name"] == team2_response.json()["name"]

    def test_team_name_validation(self, client: TestClient, setup_organization):
        """Test team name validation rules"""
        org_id = setup_organization

        # Test empty name
        team_data = {"organization_id": org_id, "name": "", "team_type": "development"}
        response = client.post("/teams", json=team_data)
        assert response.status_code == 422

        # Test very long name
        long_name = "x" * 256
        team_data = {
            "organization_id": org_id,
            "name": long_name,
            "team_type": "development",
        }
        response = client.post("/teams", json=team_data)
        assert response.status_code == 422

        # Test name with special characters (should be allowed)
        team_data = {
            "organization_id": org_id,
            "name": "Dev Team #1 (Front-end & Back-end)",
            "team_type": "development",
        }
        response = client.post("/teams", json=team_data)
        assert response.status_code == 201
