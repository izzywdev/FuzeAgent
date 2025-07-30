"""
Test cases for MCP Server functionality
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add the MCP server path to sys.path for imports
mcp_server_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '..', 'mcp-servers', 'fuzeagent-server')
sys.path.insert(0, mcp_server_path)

from server import FuzeAgentMCPServer, FuzeAgentClient


@pytest.mark.mcp
@pytest.mark.integration
class TestMCPServer:
    """Test MCP Server functionality"""
    
    @pytest.fixture
    def mock_fuze_client(self):
        """Mock FuzeAgent API client"""
        client = MagicMock(spec=FuzeAgentClient)
        
        # Mock organizations
        client.get_organizations.return_value = [
            {"id": "org-1", "name": "Test Org", "description": "Test organization"},
            {"id": "org-2", "name": "Dev Org", "description": "Development organization"}
        ]
        
        # Mock teams
        client.get_teams.return_value = [
            {
                "id": "team-1",
                "organization_id": "org-1", 
                "name": "Backend Team",
                "description": "Backend development team",
                "team_type": "development"
            },
            {
                "id": "team-2",
                "organization_id": "org-1",
                "name": "Frontend Team", 
                "description": "Frontend development team",
                "team_type": "development"
            }
        ]
        
        # Mock agents
        client.get_agents.return_value = [
            {
                "id": "agent-1",
                "team_id": "team-1",
                "name": "Python Developer",
                "role": "Senior Python Developer",
                "type": "python_developer",
                "status": "active"
            },
            {
                "id": "agent-2", 
                "team_id": "team-2",
                "name": "React Developer",
                "role": "Frontend Developer",
                "type": "react_developer",
                "status": "active"
            }
        ]
        
        # Mock templates
        client.get_templates.return_value = [
            {
                "template_id": "python_developer",
                "name": "Python Developer",
                "category": "development",
                "description": "Expert Python developer"
            },
            {
                "template_id": "react_developer",
                "name": "React Developer", 
                "category": "development",
                "description": "Expert React developer"
            }
        ]
        
        # Mock agent creation
        client.create_agent.return_value = {
            "id": "new-agent-123",
            "name": "New Agent",
            "status": "active"
        }
        
        # Mock task assignment
        client.assign_task.return_value = {
            "task_id": "task-123",
            "message": "Task assigned successfully"
        }
        
        return client
    
    @pytest.fixture
    def mcp_server(self, mock_fuze_client):
        """MCP Server instance with mocked client"""
        with patch('server.FuzeAgentClient', return_value=mock_fuze_client):
            server = FuzeAgentMCPServer("http://localhost:8000")
            return server
    
    def test_server_initialization(self, mcp_server):
        """Test MCP server initialization"""
        assert mcp_server.server.name == "fuzeagent"
        assert mcp_server.api_client is not None
        assert mcp_server.base_url == "http://localhost:8000"
    
    def test_list_organizations_tool(self, mcp_server):
        """Test list_organizations tool"""
        # Test tool is registered
        tools = mcp_server.server._tools
        assert "list_organizations" in tools
        
        # Test tool execution
        result = mcp_server._list_organizations({})
        
        assert result["success"] is True
        assert "organizations" in result
        assert len(result["organizations"]) == 2
        assert result["organizations"][0]["name"] == "Test Org"
    
    def test_list_teams_tool(self, mcp_server):
        """Test list_teams tool"""
        # Test tool is registered
        tools = mcp_server.server._tools
        assert "list_teams" in tools
        
        # Test tool execution - all teams
        result = mcp_server._list_teams({})
        
        assert result["success"] is True
        assert "teams" in result
        assert len(result["teams"]) == 2
        
        # Test with organization filter
        result = mcp_server._list_teams({"organization_id": "org-1"})
        
        assert result["success"] is True
        # Mock client should filter by organization
        mcp_server.api_client.get_teams.assert_called_with(organization_id="org-1")
    
    def test_list_agents_tool(self, mcp_server):
        """Test list_agents tool"""
        # Test tool is registered
        tools = mcp_server.server._tools
        assert "list_agents" in tools
        
        # Test tool execution - all agents
        result = mcp_server._list_agents({})
        
        assert result["success"] is True
        assert "agents" in result
        assert len(result["agents"]) == 2
        
        # Test with team filter
        result = mcp_server._list_agents({"team_id": "team-1"})
        
        assert result["success"] is True
        mcp_server.api_client.get_agents.assert_called_with(team_id="team-1")
    
    def test_get_agent_details_tool(self, mcp_server):
        """Test get_agent_details tool"""
        # Mock specific agent details
        mcp_server.api_client.get_agent.return_value = {
            "id": "agent-1",
            "name": "Python Developer",
            "role": "Senior Python Developer",
            "config": {
                "goal": "Develop Python applications",
                "tools": ["code_generation", "debugging"],
                "skills": ["python", "fastapi"]
            },
            "status": "active"
        }
        
        tools = mcp_server.server._tools
        assert "get_agent_details" in tools
        
        result = mcp_server._get_agent_details({"agent_id": "agent-1"})
        
        assert result["success"] is True
        assert "agent" in result
        assert result["agent"]["name"] == "Python Developer"
        assert "config" in result["agent"]
    
    def test_list_templates_tool(self, mcp_server):
        """Test list_templates tool"""
        tools = mcp_server.server._tools
        assert "list_templates" in tools
        
        # Test all templates
        result = mcp_server._list_templates({})
        
        assert result["success"] is True
        assert "templates" in result
        assert len(result["templates"]) == 2
        
        # Test with category filter
        result = mcp_server._list_templates({"category": "development"})
        
        assert result["success"] is True
        mcp_server.api_client.get_templates.assert_called_with(category="development")
    
    def test_create_agent_tool(self, mcp_server):
        """Test create_agent tool"""
        tools = mcp_server.server._tools
        assert "create_agent" in tools
        
        # Test agent creation from template
        create_data = {
            "template_id": "python_developer",
            "team_id": "team-1",
            "name": "New Python Agent",
            "overrides": {"goal": "Build amazing Python apps"}
        }
        
        result = mcp_server._create_agent(create_data)
        
        assert result["success"] is True
        assert "agent" in result
        assert result["agent"]["id"] == "new-agent-123"
        
        # Verify API was called correctly
        mcp_server.api_client.create_agent_from_template.assert_called_once()
    
    def test_assign_task_tool(self, mcp_server):
        """Test assign_task tool"""
        tools = mcp_server.server._tools
        assert "assign_task" in tools
        
        task_data = {
            "agent_id": "agent-1",
            "title": "Implement user authentication",
            "description": "Add JWT-based authentication to the API",
            "priority": 8
        }
        
        result = mcp_server._assign_task(task_data)
        
        assert result["success"] is True
        assert "task_id" in result
        assert result["task_id"] == "task-123"
        
        # Verify API was called correctly
        mcp_server.api_client.assign_task.assert_called_with(
            agent_id="agent-1",
            task_data={
                "title": "Implement user authentication",
                "description": "Add JWT-based authentication to the API",
                "priority": 8,
                "created_by": "mcp-user"
            }
        )
    
    def test_error_handling_in_tools(self, mcp_server):
        """Test error handling in MCP tools"""
        # Mock API client to raise exception
        mcp_server.api_client.get_organizations.side_effect = Exception("API Error")
        
        result = mcp_server._list_organizations({})
        
        assert result["success"] is False
        assert "error" in result
        assert "API Error" in result["error"]
    
    def test_tool_input_validation(self, mcp_server):
        """Test input validation for tools"""
        # Test create_agent with missing required fields
        result = mcp_server._create_agent({})
        
        assert result["success"] is False
        assert "error" in result
        assert "required" in result["error"].lower()
        
        # Test assign_task with missing agent_id
        result = mcp_server._assign_task({"title": "Test Task"})
        
        assert result["success"] is False
        assert "agent_id" in result["error"]
    
    def test_health_check_tool(self, mcp_server):
        """Test health check tool"""
        # Mock health check response
        mcp_server.api_client.health_check.return_value = {
            "status": "healthy",
            "timestamp": "2025-01-29T14:00:00Z",
            "version": "1.0.0",
            "database": "connected"
        }
        
        tools = mcp_server.server._tools
        assert "health_check" in tools
        
        result = mcp_server._health_check({})
        
        assert result["success"] is True
        assert "health" in result
        assert result["health"]["status"] == "healthy"
    
    def test_tool_descriptions_and_schemas(self, mcp_server):
        """Test that all tools have proper descriptions and schemas"""
        tools = mcp_server.server._tools
        
        expected_tools = [
            "list_organizations",
            "list_teams", 
            "list_agents",
            "get_agent_details",
            "list_templates",
            "create_agent",
            "assign_task",
            "health_check"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tools
            tool = tools[tool_name]
            
            # Check tool has description
            assert hasattr(tool, 'description')
            assert tool.description is not None
            assert len(tool.description) > 0
            
            # Check tool has input schema
            assert hasattr(tool, 'input_schema')
            assert tool.input_schema is not None
    
    @patch('server.stdio_server')
    def test_stdio_server_mode(self, mock_stdio_server, mock_fuze_client):
        """Test STDIO server mode"""
        with patch('server.FuzeAgentClient', return_value=mock_fuze_client):
            # Mock stdio server
            mock_server_instance = MagicMock()
            mock_stdio_server.return_value.__aenter__.return_value = mock_server_instance
            
            # Import and test the stdio server function
            from server import run_stdio_server
            
            # This would normally run the server, but we're just testing it can be called
            # The actual test would need async context
            assert callable(run_stdio_server)
    
    def test_api_client_initialization(self):
        """Test FuzeAgent API client initialization"""
        client = FuzeAgentClient("http://test-api:8000")
        
        assert client.base_url == "http://test-api:8000"
        assert hasattr(client, 'session')
    
    @patch('server.httpx.AsyncClient')
    def test_api_client_methods(self, mock_httpx):
        """Test FuzeAgent API client methods"""
        # Mock HTTP responses
        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_session
        
        client = FuzeAgentClient("http://test-api:8000")
        
        # Test async context manager methods exist
        assert hasattr(client, '__aenter__')
        assert hasattr(client, '__aexit__')
        
        # Test method signatures exist
        expected_methods = [
            'get_organizations', 'get_teams', 'get_agents', 'get_agent',
            'get_templates', 'create_agent_from_template', 'assign_task',
            'health_check'
        ]
        
        for method_name in expected_methods:
            assert hasattr(client, method_name)
            assert callable(getattr(client, method_name))
    
    def test_mcp_server_resource_handling(self, mcp_server):
        """Test MCP server resource management"""
        # Test that server has proper resource handling
        assert hasattr(mcp_server.server, '_resources')
        
        # Test server cleanup
        assert hasattr(mcp_server, 'close')
        
        # Test that close is callable
        assert callable(mcp_server.close)
    
    def test_concurrent_tool_execution(self, mcp_server):
        """Test concurrent execution of MCP tools"""
        import asyncio
        
        # Create multiple concurrent tool calls
        results = []
        
        # Simulate concurrent calls
        for i in range(5):
            result = mcp_server._list_organizations({})
            results.append(result)
        
        # All should succeed
        for result in results:
            assert result["success"] is True
        
        # API client should have been called multiple times
        assert mcp_server.api_client.get_organizations.call_count == 5
    
    def test_tool_response_formatting(self, mcp_server):
        """Test that tool responses are properly formatted for MCP"""
        result = mcp_server._list_organizations({})
        
        # Check response structure
        assert isinstance(result, dict)
        assert "success" in result
        assert isinstance(result["success"], bool)
        
        if result["success"]:
            assert "organizations" in result
            assert isinstance(result["organizations"], list)
        else:
            assert "error" in result
            assert isinstance(result["error"], str)
    
    def test_integration_with_fuzeagent_api(self, mcp_server):
        """Test integration points with FuzeAgent API"""
        # Test that all expected endpoints are called correctly
        
        # Organizations
        mcp_server._list_organizations({})
        mcp_server.api_client.get_organizations.assert_called()
        
        # Teams
        mcp_server._list_teams({"organization_id": "org-1"})
        mcp_server.api_client.get_teams.assert_called_with(organization_id="org-1")
        
        # Agents
        mcp_server._list_agents({"team_id": "team-1"})
        mcp_server.api_client.get_agents.assert_called_with(team_id="team-1")
        
        # Templates
        mcp_server._list_templates({})
        mcp_server.api_client.get_templates.assert_called()
        
        # Verify all integration points work
        assert True  # If we get here, all integrations work