"""
Test cases for Organizations API endpoints
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
@pytest.mark.database
class TestOrganizationsAPI:
    """Test Organization API endpoints"""
    
    def test_get_organizations_empty(self, client: TestClient):
        """Test getting organizations when none exist"""
        response = client.get("/organizations")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_create_organization(self, client: TestClient):
        """Test creating a new organization"""
        org_data = {
            "name": "Test Organization",
            "description": "A test organization",
            "settings": {"timezone": "UTC"}
        }
        
        response = client.post("/organizations", json=org_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == org_data["name"]
        assert data["description"] == org_data["description"]
        assert data["settings"] == org_data["settings"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_organization_missing_fields(self, client: TestClient):
        """Test creating organization with missing required fields"""
        org_data = {"description": "Missing name"}
        
        response = client.post("/organizations", json=org_data)
        assert response.status_code == 422  # Validation error
    
    def test_get_organization_by_id(self, client: TestClient):
        """Test getting organization by ID"""
        # First create an organization
        org_data = {
            "name": "Test Organization",
            "description": "A test organization"
        }
        create_response = client.post("/organizations", json=org_data)
        org_id = create_response.json()["id"]
        
        # Get the organization
        response = client.get(f"/organizations/{org_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == org_id
        assert data["name"] == org_data["name"]
    
    def test_get_organization_not_found(self, client: TestClient):
        """Test getting non-existent organization"""
        fake_id = "550e8400-e29b-41d4-a716-446655440999"
        response = client.get(f"/organizations/{fake_id}")
        assert response.status_code == 404
    
    def test_update_organization(self, client: TestClient):
        """Test updating organization"""
        # Create organization
        org_data = {
            "name": "Original Organization",
            "description": "Original description"
        }
        create_response = client.post("/organizations", json=org_data)
        org_id = create_response.json()["id"]
        
        # Update organization
        update_data = {
            "name": "Updated Organization",
            "description": "Updated description"
        }
        response = client.put(f"/organizations/{org_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    def test_update_organization_not_found(self, client: TestClient):
        """Test updating non-existent organization"""
        fake_id = "550e8400-e29b-41d4-a716-446655440999"
        update_data = {"name": "Updated Name"}
        
        response = client.put(f"/organizations/{fake_id}", json=update_data)
        assert response.status_code == 404
    
    def test_delete_organization(self, client: TestClient):
        """Test deleting organization"""
        # Create organization
        org_data = {
            "name": "To Be Deleted",
            "description": "This will be deleted"
        }
        create_response = client.post("/organizations", json=org_data)
        org_id = create_response.json()["id"]
        
        # Delete organization
        response = client.delete(f"/organizations/{org_id}")
        assert response.status_code == 200
        assert "message" in response.json()
        
        # Verify deletion
        get_response = client.get(f"/organizations/{org_id}")
        assert get_response.status_code == 404
    
    def test_delete_organization_not_found(self, client: TestClient):
        """Test deleting non-existent organization"""
        fake_id = "550e8400-e29b-41d4-a716-446655440999"
        
        response = client.delete(f"/organizations/{fake_id}")
        assert response.status_code == 404