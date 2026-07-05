"""
MCP (Model Context Protocol) Integration for FuzeAgent

Provides MCP server functionality to give Claude SDK sessions access to:
- Organization structure and context
- Team information and agent hierarchy
- Agent capabilities and current status
- Task context and history
- Repository and project information

This allows agents to have full organizational context when making decisions.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict

from .database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Represents an MCP tool definition"""

    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPResource:
    """Represents an MCP resource"""

    uri: str
    name: str
    description: str
    mime_type: str


class FuzeAgentMCPServer:
    """
    MCP Server for FuzeAgent organizational context.

    Provides tools and resources for Claude SDK sessions to access:
    - Organizational structure
    - Agent capabilities and status
    - Task context and history
    - Repository information
    """

    def __init__(self):
        self.tools = self._define_tools()
        self.resources = self._define_resources()

    def _define_tools(self) -> List[MCPTool]:
        """Define available MCP tools"""
        return [
            MCPTool(
                name="get_organization_structure",
                description="Get the complete organizational structure including teams and agents",
                input_schema={
                    "type": "object",
                    "properties": {
                        "organization_id": {
                            "type": "string",
                            "description": "Optional organization ID to filter by",
                        }
                    },
                },
            ),
            MCPTool(
                name="get_team_agents",
                description="Get all agents in a specific team with their capabilities",
                input_schema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "Team ID to get agents for",
                        }
                    },
                    "required": ["team_id"],
                },
            ),
            MCPTool(
                name="get_agent_status",
                description="Get current status and capabilities of a specific agent",
                input_schema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "Agent ID to get status for",
                        }
                    },
                    "required": ["agent_id"],
                },
            ),
            MCPTool(
                name="get_task_context",
                description="Get comprehensive context for a task including history and related tasks",
                input_schema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID to get context for",
                        },
                        "include_history": {
                            "type": "boolean",
                            "description": "Whether to include task execution history",
                            "default": True,
                        },
                    },
                    "required": ["task_id"],
                },
            ),
            MCPTool(
                name="get_agent_memory",
                description="Get agent memory and previous interactions",
                input_schema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "Agent ID to get memory for",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of memory items to return",
                            "default": 10,
                        },
                        "memory_type": {
                            "type": "string",
                            "description": "Type of memory to retrieve",
                            "enum": [
                                "interactions",
                                "code_generations",
                                "performance_metrics",
                            ],
                            "default": "interactions",
                        },
                    },
                    "required": ["agent_id"],
                },
            ),
            MCPTool(
                name="search_similar_tasks",
                description="Search for similar tasks based on description or requirements",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for similar tasks",
                        },
                        "agent_type": {
                            "type": "string",
                            "description": "Optional agent type to filter results",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
            MCPTool(
                name="get_repository_context",
                description="Get repository context and recent changes",
                input_schema={
                    "type": "object",
                    "properties": {
                        "repository_url": {
                            "type": "string",
                            "description": "Repository URL to get context for",
                        },
                        "branch": {
                            "type": "string",
                            "description": "Optional branch name",
                            "default": "main",
                        },
                    },
                    "required": ["repository_url"],
                },
            ),
            MCPTool(
                name="get_agent_recommendations",
                description="Get agent recommendations for a specific task type",
                input_schema={
                    "type": "object",
                    "properties": {
                        "task_description": {
                            "type": "string",
                            "description": "Description of the task",
                        },
                        "required_skills": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of required skills",
                        },
                        "exclude_busy": {
                            "type": "boolean",
                            "description": "Whether to exclude currently busy agents",
                            "default": True,
                        },
                    },
                    "required": ["task_description"],
                },
            ),
        ]

    def _define_resources(self) -> List[MCPResource]:
        """Define available MCP resources"""
        return [
            MCPResource(
                uri="fuzeagent://organizations",
                name="Organizations",
                description="Complete organizational structure and hierarchy",
                mime_type="application/json",
            ),
            MCPResource(
                uri="fuzeagent://agent-templates",
                name="Agent Templates",
                description="Available agent templates and their capabilities",
                mime_type="application/json",
            ),
            MCPResource(
                uri="fuzeagent://system-status",
                name="System Status",
                description="Current system status and health metrics",
                mime_type="application/json",
            ),
        ]

    async def handle_tool_call(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle MCP tool calls"""
        try:
            if tool_name == "get_organization_structure":
                return await self._get_organization_structure(arguments)
            elif tool_name == "get_team_agents":
                return await self._get_team_agents(arguments)
            elif tool_name == "get_agent_status":
                return await self._get_agent_status(arguments)
            elif tool_name == "get_task_context":
                return await self._get_task_context(arguments)
            elif tool_name == "get_agent_memory":
                return await self._get_agent_memory(arguments)
            elif tool_name == "search_similar_tasks":
                return await self._search_similar_tasks(arguments)
            elif tool_name == "get_repository_context":
                return await self._get_repository_context(arguments)
            elif tool_name == "get_agent_recommendations":
                return await self._get_agent_recommendations(arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Error in MCP tool call {tool_name}: {e}")
            return {"error": str(e)}

    async def handle_resource_request(self, uri: str) -> Dict[str, Any]:
        """Handle MCP resource requests"""
        try:
            if uri == "fuzeagent://organizations":
                return await self._get_organizations_resource()
            elif uri == "fuzeagent://agent-templates":
                return await self._get_agent_templates_resource()
            elif uri == "fuzeagent://system-status":
                return await self._get_system_status_resource()
            else:
                return {"error": f"Unknown resource: {uri}"}

        except Exception as e:
            logger.error(f"Error in MCP resource request {uri}: {e}")
            return {"error": str(e)}

    # Tool implementations

    async def _get_organization_structure(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get organizational structure"""
        organization_id = args.get("organization_id")

        # This would integrate with the MCP FuzeAgent server
        # For now, return mock structure
        return {
            "organizations": [
                {
                    "id": "fuzeagent-org",
                    "name": "FuzeAgent Organization",
                    "teams": [
                        {
                            "id": "dev-team-1",
                            "name": "Development Team Alpha",
                            "agents": [
                                {
                                    "id": "frontend-dev-1",
                                    "name": "React Developer 1",
                                    "type": "frontend_developer",
                                    "status": "available",
                                    "skills": ["react", "typescript", "css"],
                                },
                                {
                                    "id": "backend-dev-1",
                                    "name": "Python Developer 1",
                                    "type": "backend_developer",
                                    "status": "busy",
                                    "skills": ["python", "fastapi", "postgresql"],
                                },
                            ],
                        }
                    ],
                }
            ]
        }

    async def _get_team_agents(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get agents in a team"""
        team_id = args["team_id"]

        # Get agents from database
        agents = await DatabaseManager.get_agents_by_team(team_id)

        return {
            "team_id": team_id,
            "agents": [
                {
                    "id": agent["id"],
                    "name": agent["name"],
                    "role": agent["role"],
                    "type": agent["type"],
                    "status": agent["status"],
                    "capabilities": agent.get("config", {}).get("tools", []),
                    "current_task": agent.get("current_task_id"),
                    "created_at": agent["created_at"].isoformat()
                    if agent["created_at"]
                    else None,
                }
                for agent in agents
            ],
        }

    async def _get_agent_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get agent status"""
        agent_id = args["agent_id"]

        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            return {"error": f"Agent {agent_id} not found"}

        # Get current tasks
        tasks = await DatabaseManager.get_agent_tasks(agent_id, limit=5)

        return {
            "agent_id": agent_id,
            "name": agent["name"],
            "role": agent["role"],
            "type": agent["type"],
            "status": agent["status"],
            "capabilities": agent.get("config", {}).get("tools", []),
            "model": agent.get("config", {}).get("model", "claude-sonnet-4-20250514"),
            "current_tasks": [
                {
                    "id": task["id"],
                    "title": task["title"],
                    "status": task["status"],
                    "created_at": task["created_at"].isoformat()
                    if task["created_at"]
                    else None,
                }
                for task in tasks
                if task["status"] in ["pending", "executing"]
            ],
            "recent_tasks": [
                {
                    "id": task["id"],
                    "title": task["title"],
                    "status": task["status"],
                    "completed_at": task["updated_at"].isoformat()
                    if task["updated_at"]
                    else None,
                }
                for task in tasks
                if task["status"] in ["completed", "failed"]
            ],
        }

    async def _get_task_context(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get task context"""
        task_id = args["task_id"]
        include_history = args.get("include_history", True)

        # Get task data
        task = await DatabaseManager.get_task(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}

        # Get agent data
        agent = (
            await DatabaseManager.get_agent(task["assigned_to"])
            if task["assigned_to"]
            else None
        )

        context = {
            "task_id": task_id,
            "title": task["title"],
            "description": task["description"],
            "status": task["status"],
            "priority": task.get("priority", "medium"),
            "created_at": task["created_at"].isoformat()
            if task["created_at"]
            else None,
            "assigned_agent": {
                "id": agent["id"],
                "name": agent["name"],
                "role": agent["role"],
                "type": agent["type"],
            }
            if agent
            else None,
        }

        if include_history:
            # Get task iterations
            iterations = await DatabaseManager.get_task_iterations(task_id)
            context["execution_history"] = [
                {
                    "iteration": iter["iteration_number"],
                    "step": iter["step"],
                    "started_at": iter["started_at"].isoformat()
                    if iter["started_at"]
                    else None,
                    "completed_at": iter["completed_at"].isoformat()
                    if iter["completed_at"]
                    else None,
                    "success": iter["success"],
                    "human_question": iter["human_question"],
                    "human_response": iter["human_response"],
                }
                for iter in iterations
            ]

        return context

    async def _get_agent_memory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get agent memory"""
        agent_id = args["agent_id"]
        limit = args.get("limit", 10)
        memory_type = args.get("memory_type", "interactions")

        # This would integrate with conversation_manager
        # For now return mock data
        return {
            "agent_id": agent_id,
            "memory_type": memory_type,
            "items": [
                {
                    "id": f"memory-{i}",
                    "type": memory_type,
                    "content": f"Sample {memory_type} {i}",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {},
                }
                for i in range(min(limit, 5))
            ],
        }

    async def _search_similar_tasks(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search for similar tasks"""
        query = args["query"]
        agent_type = args.get("agent_type")
        limit = args.get("limit", 5)

        # This would use vector search in production
        # For now return mock results
        return {
            "query": query,
            "results": [
                {
                    "task_id": f"task-{i}",
                    "title": f"Similar task {i}",
                    "description": f"Task similar to '{query}'",
                    "similarity_score": 0.8 - (i * 0.1),
                    "agent_type": agent_type or "developer",
                    "status": "completed",
                    "completion_time_minutes": 120 + (i * 30),
                }
                for i in range(min(limit, 3))
            ],
        }

    async def _get_repository_context(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get repository context"""
        repository_url = args["repository_url"]
        branch = args.get("branch", "main")

        return {
            "repository_url": repository_url,
            "branch": branch,
            "recent_commits": [
                {
                    "hash": "abc123",
                    "message": "Recent commit message",
                    "author": "developer@example.com",
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "active_branches": [branch, "develop", "feature/new-feature"],
            "technologies": ["python", "fastapi", "react", "typescript"],
            "structure": {
                "backend": "services/orchestrator/",
                "frontend": "services/ui-react/",
                "containers": "containers/",
                "docs": "docs/",
            },
        }

    async def _get_agent_recommendations(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get agent recommendations for a task"""
        task_description = args["task_description"]
        required_skills = args.get("required_skills", [])
        exclude_busy = args.get("exclude_busy", True)

        # This would use ML/AI to match agents to tasks
        # For now return mock recommendations
        return {
            "task_description": task_description,
            "required_skills": required_skills,
            "recommendations": [
                {
                    "agent_id": "frontend-dev-1",
                    "name": "React Developer 1",
                    "match_score": 0.95,
                    "matching_skills": ["react", "typescript"],
                    "availability": "available",
                    "estimated_completion_time": "4-6 hours",
                },
                {
                    "agent_id": "fullstack-dev-1",
                    "name": "Full Stack Developer 1",
                    "match_score": 0.85,
                    "matching_skills": ["react", "python"],
                    "availability": "busy_until_2pm",
                    "estimated_completion_time": "6-8 hours",
                },
            ],
        }

    # Resource implementations

    async def _get_organizations_resource(self) -> Dict[str, Any]:
        """Get organizations resource"""
        organizations = await DatabaseManager.get_organizations()
        return {"content": organizations, "mime_type": "application/json"}

    async def _get_agent_templates_resource(self) -> Dict[str, Any]:
        """Get agent templates resource"""
        templates = await DatabaseManager.get_agent_templates()
        return {"content": templates, "mime_type": "application/json"}

    async def _get_system_status_resource(self) -> Dict[str, Any]:
        """Get system status resource"""
        return {
            "content": {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "active_agents": 5,
                "running_tasks": 3,
                "system_load": 0.45,
                "memory_usage": 0.67,
            },
            "mime_type": "application/json",
        }


# MCP Server Integration with Claude SDK
class MCPClaudeIntegration:
    """Integrates MCP server with Claude SDK sessions"""

    def __init__(self, mcp_server: FuzeAgentMCPServer):
        self.mcp_server = mcp_server

    async def setup_claude_session_mcp(
        self, session_id: str, agent_id: str, task_id: str
    ) -> Dict[str, str]:
        """Set up MCP tools for a Claude SDK session"""

        # Generate MCP server configuration for the session
        mcp_config = {
            "server_name": f"fuzeagent-{session_id}",
            "server_command": ["python", "-m", "services.orchestrator.mcp_integration"],
            "server_args": [
                "--session-id",
                session_id,
                "--agent-id",
                agent_id,
                "--task-id",
                task_id,
            ],
            "environment": {
                "FUZEAGENT_SESSION_ID": session_id,
                "FUZEAGENT_AGENT_ID": agent_id,
                "FUZEAGENT_TASK_ID": task_id,
            },
        }

        # In production, this would configure Claude SDK to use this MCP server
        # For now, return the configuration
        return mcp_config

    async def get_session_context(
        self, session_id: str, agent_id: str, task_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive context for a Claude SDK session"""

        # Get agent context
        agent_context = await self.mcp_server.handle_tool_call(
            "get_agent_status", {"agent_id": agent_id}
        )

        # Get task context
        task_context = await self.mcp_server.handle_tool_call(
            "get_task_context", {"task_id": task_id}
        )

        # Get team context
        if agent_context.get("team_id"):
            team_context = await self.mcp_server.handle_tool_call(
                "get_team_agents", {"team_id": agent_context["team_id"]}
            )
        else:
            team_context = {"agents": []}

        return {
            "session_id": session_id,
            "agent_context": agent_context,
            "task_context": task_context,
            "team_context": team_context,
            "available_tools": [tool.name for tool in self.mcp_server.tools],
            "available_resources": [
                resource.uri for resource in self.mcp_server.resources
            ],
        }
