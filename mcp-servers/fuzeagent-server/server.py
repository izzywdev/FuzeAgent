#!/usr/bin/env python3
"""
FuzeAgent MCP Server

A Model Context Protocol server that exposes FuzeAgent organizations, teams, and agents
as tools for integration with Claude Desktop and other MCP clients.
"""

import asyncio
import os
import json
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from mcp.types import (
    Tool,
    TextContent,
    CallToolRequest,
    CallToolResult,
    ListToolsRequest
)
from pydantic import BaseModel, Field
import structlog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

class FuzeAgentClient:
    """HTTP client for FuzeAgent API communication"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request to FuzeAgent API"""
        url = urljoin(self.base_url, endpoint)
        try:
            response = await self.client.get(url, params=params or {})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("API request failed", url=url, error=str(e))
            raise RuntimeError(f"Failed to fetch data from {url}: {e}")
    
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request to FuzeAgent API"""
        url = urljoin(self.base_url, endpoint)
        try:
            response = await self.client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("API request failed", url=url, error=str(e))
            raise RuntimeError(f"Failed to post data to {url}: {e}")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

class FuzeAgentMCPServer:
    """MCP Server for FuzeAgent integration with support for stdio and SSE transport"""
    
    def __init__(self, api_url: str):
        self.api_client = FuzeAgentClient(api_url)
        self.server = Server("fuzeagent")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="list_organizations",
                    description="List all organizations in the FuzeAgent system",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="list_teams",
                    description="List teams, optionally filtered by organization",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "organization_id": {
                                "type": "string",
                                "description": "Optional organization ID to filter teams"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="list_agents",
                    description="List agents, optionally filtered by team or skills",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_id": {
                                "type": "string",
                                "description": "Optional team ID to filter agents"
                            },
                            "skills": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of required skills"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_agent_details",
                    description="Get detailed information about a specific agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "ID of the agent to get details for"
                            }
                        },
                        "required": ["agent_id"]
                    }
                ),
                Tool(
                    name="assign_task",
                    description="Assign a task to a specific agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "ID of the agent to assign the task to"
                            },
                            "title": {
                                "type": "string",
                                "description": "Title of the task"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of the task"
                            },
                            "priority": {
                                "type": "integer",
                                "description": "Task priority (1-10, default: 5)",
                                "minimum": 1,
                                "maximum": 10,
                                "default": 5
                            },
                            "created_by": {
                                "type": "string",
                                "description": "ID or name of task creator",
                                "default": "claude-mcp-client"
                            }
                        },
                        "required": ["agent_id", "title", "description"]
                    }
                ),
                Tool(
                    name="get_agent_templates",
                    description="List available agent templates with their capabilities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Optional category filter (development, qa, devops, business, management, hybrid)"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_team_hierarchy",
                    description="Get hierarchical view of organization → teams → agents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "organization_id": {
                                "type": "string",
                                "description": "Optional organization ID to filter hierarchy"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="deploy_agent",
                    description="Deploy a new agent from a template to a specific team",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_id": {
                                "type": "string",
                                "description": "ID of the team to deploy the agent to"
                            },
                            "template_id": {
                                "type": "string",
                                "description": "ID of the agent template to use (e.g., 'python_developer', 'react_developer')"
                            },
                            "name": {
                                "type": "string",
                                "description": "Custom name for the agent instance"
                            },
                            "description": {
                                "type": "string",
                                "description": "Optional description for the agent instance"
                            },
                            "overrides": {
                                "type": "object",
                                "description": "Optional configuration overrides for the agent",
                                "properties": {
                                    "model": {"type": "string"},
                                    "temperature": {"type": "number", "minimum": 0, "maximum": 2},
                                    "max_tokens": {"type": "integer"},
                                    "skills": {"type": "array", "items": {"type": "string"}},
                                    "tools": {"type": "array", "items": {"type": "string"}}
                                }
                            }
                        },
                        "required": ["team_id", "template_id", "name"]
                    }
                ),
                Tool(
                    name="create_custom_agent",
                    description="Create a custom agent with specific configuration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_id": {
                                "type": "string",
                                "description": "ID of the team to create the agent in"
                            },
                            "name": {
                                "type": "string",
                                "description": "Name for the custom agent"
                            },
                            "role": {
                                "type": "string",
                                "description": "Role description for the agent"
                            },
                            "type": {
                                "type": "string",
                                "description": "Agent type identifier"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the agent's capabilities"
                            },
                            "config": {
                                "type": "object",
                                "description": "Agent configuration including model, skills, tools",
                                "properties": {
                                    "model": {"type": "string", "default": "claude-3-sonnet-20241022"},
                                    "temperature": {"type": "number", "minimum": 0, "maximum": 2, "default": 0.7},
                                    "max_tokens": {"type": "integer", "default": 4096},
                                    "skills": {"type": "array", "items": {"type": "string"}},
                                    "tools": {"type": "array", "items": {"type": "string"}},
                                    "system_prompt": {"type": "string"}
                                }
                            }
                        },
                        "required": ["team_id", "name", "role", "type"]
                    }
                ),
                Tool(
                    name="get_agent_tasks",
                    description="Get list of tasks assigned to a specific agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "ID of the agent to get tasks for"
                            },
                            "status": {
                                "type": "string",
                                "description": "Optional filter by task status",
                                "enum": ["pending", "running", "completed", "failed", "cancelled"]
                            }
                        },
                        "required": ["agent_id"]
                    }
                ),
                Tool(
                    name="update_task_status",
                    description="Update the status of a specific task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "ID of the task to update"
                            },
                            "status": {
                                "type": "string",
                                "description": "New status for the task",
                                "enum": ["pending", "running", "completed", "failed", "cancelled"]
                            },
                            "result": {
                                "type": "string",
                                "description": "Optional task result or notes"
                            }
                        },
                        "required": ["task_id", "status"]
                    }
                ),
                # Goals Management Tools
                Tool(
                    name="create_organizational_goal",
                    description="Create a new strategic goal for an organization",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "organization_id": {
                                "type": "string",
                                "description": "ID of the organization"
                            },
                            "title": {
                                "type": "string",
                                "description": "Goal title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed goal description"
                            },
                            "goal_type": {
                                "type": "string",
                                "enum": ["business", "technical", "operational", "strategic"],
                                "description": "Type of goal"
                            },
                            "target_value": {
                                "type": "number",
                                "description": "Target numeric value (e.g., revenue, users)"
                            },
                            "target_unit": {
                                "type": "string",
                                "description": "Unit for target value (e.g., USD, users, percent)"
                            },
                            "target_deadline": {
                                "type": "string",
                                "description": "Deadline in YYYY-MM-DD format"
                            },
                            "priority_level": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 10,
                                "description": "Priority level (1-10, higher is more important)"
                            },
                            "assigned_teams": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of team IDs assigned to this goal"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Tags for categorization"
                            }
                        },
                        "required": ["organization_id", "title", "description", "goal_type", "target_deadline"]
                    }
                ),
                Tool(
                    name="list_organization_goals",
                    description="List all goals for an organization",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "organization_id": {
                                "type": "string",
                                "description": "ID of the organization"
                            },
                            "status": {
                                "type": "array",
                                "items": {"type": "string", "enum": ["active", "paused", "completed", "cancelled"]},
                                "description": "Filter by goal status"
                            },
                            "goal_type": {
                                "type": "array",
                                "items": {"type": "string", "enum": ["business", "technical", "operational", "strategic"]},
                                "description": "Filter by goal type"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 25,
                                "description": "Maximum number of goals to return"
                            }
                        },
                        "required": ["organization_id"]
                    }
                ),
                Tool(
                    name="get_goal_details",
                    description="Get detailed information about a specific goal",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal"
                            }
                        },
                        "required": ["goal_id"]
                    }
                ),
                Tool(
                    name="update_goal_progress",
                    description="Update progress on a goal",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal"
                            },
                            "progress_percentage": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100,
                                "description": "Progress percentage (0-100)"
                            },
                            "current_value": {
                                "type": "number",
                                "description": "Current value achieved"
                            },
                            "completion_confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "Confidence in completion (0-1)"
                            },
                            "notes": {
                                "type": "string",
                                "description": "Progress notes"
                            }
                        },
                        "required": ["goal_id"]
                    }
                ),
                Tool(
                    name="generate_goal_execution_plan",
                    description="Generate comprehensive execution plan with AI-powered milestones and tasks",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal"
                            },
                            "planning_context": {
                                "type": "object",
                                "description": "Optional context for AI planning",
                                "properties": {
                                    "focus": {"type": "string"},
                                    "resources": {"type": "string"},
                                    "constraints": {"type": "array", "items": {"type": "string"}}
                                }
                            }
                        },
                        "required": ["goal_id"]
                    }
                ),
                Tool(
                    name="create_goal_conversation",
                    description="Create an AI-powered planning conversation for a goal",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal"
                            },
                            "conversation_type": {
                                "type": "string",
                                "enum": ["planning", "review", "problem_solving"],
                                "description": "Type of conversation"
                            },
                            "conversation_title": {
                                "type": "string",
                                "description": "Title for the conversation"
                            },
                            "initial_context": {
                                "type": "object",
                                "description": "Initial context for the conversation"
                            }
                        },
                        "required": ["goal_id", "conversation_type", "conversation_title"]
                    }
                ),
                Tool(
                    name="track_goal_progress",
                    description="Record detailed progress tracking with risk assessment",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal"
                            },
                            "progress_percentage": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100,
                                "description": "Progress percentage (0-100)"
                            },
                            "current_value": {
                                "type": "number",
                                "description": "Current value achieved"
                            },
                            "notes": {
                                "type": "string",
                                "description": "Progress notes"
                            },
                            "confidence_score": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "Confidence score (0-1)"
                            },
                            "trigger_alerts": {
                                "type": "boolean",
                                "default": True,
                                "description": "Whether to trigger risk assessment alerts"
                            }
                        },
                        "required": ["goal_id", "progress_percentage"]
                    }
                ),
                Tool(
                    name="assess_goal_deadline_risk",
                    description="Get comprehensive risk assessment for goal completion",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal"
                            }
                        },
                        "required": ["goal_id"]
                    }
                ),
                Tool(
                    name="get_organization_goals_dashboard",
                    description="Get comprehensive dashboard view for all organizational goals",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "organization_id": {
                                "type": "string",
                                "description": "ID of the organization"
                            }
                        },
                        "required": ["organization_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls"""
            try:
                if name == "list_organizations":
                    return await self._list_organizations()
                elif name == "list_teams":
                    return await self._list_teams(arguments.get("organization_id"))
                elif name == "list_agents":
                    return await self._list_agents(
                        team_id=arguments.get("team_id"),
                        skills=arguments.get("skills")
                    )
                elif name == "get_agent_details":
                    return await self._get_agent_details(arguments["agent_id"])
                elif name == "assign_task":
                    return await self._assign_task(arguments)
                elif name == "get_agent_templates":
                    return await self._get_agent_templates(arguments.get("category"))
                elif name == "get_team_hierarchy":
                    return await self._get_team_hierarchy(arguments.get("organization_id"))
                elif name == "deploy_agent":
                    return await self._deploy_agent(arguments)
                elif name == "create_custom_agent":
                    return await self._create_custom_agent(arguments)
                elif name == "get_agent_tasks":
                    return await self._get_agent_tasks(arguments["agent_id"], arguments.get("status"))
                elif name == "update_task_status":
                    return await self._update_task_status(arguments)
                # Goals Management Tool Handlers
                elif name == "create_organizational_goal":
                    return await self._create_organizational_goal(arguments)
                elif name == "list_organization_goals":
                    return await self._list_organization_goals(arguments)
                elif name == "get_goal_details":
                    return await self._get_goal_details(arguments["goal_id"])
                elif name == "update_goal_progress":
                    return await self._update_goal_progress(arguments)
                elif name == "generate_goal_execution_plan":
                    return await self._generate_goal_execution_plan(arguments)
                elif name == "create_goal_conversation":
                    return await self._create_goal_conversation(arguments)
                elif name == "track_goal_progress":
                    return await self._track_goal_progress(arguments)
                elif name == "assess_goal_deadline_risk":
                    return await self._assess_goal_deadline_risk(arguments["goal_id"])
                elif name == "get_organization_goals_dashboard":
                    return await self._get_organization_goals_dashboard(arguments["organization_id"])
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")]
                    )
            except Exception as e:
                logger.exception("Tool call failed", tool=name, error=str(e))
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error executing {name}: {str(e)}")]
                )
    
    async def _list_organizations(self) -> CallToolResult:
        """List all organizations"""
        try:
            data = await self.api_client.get("/organizations")
            
            if not data:
                return CallToolResult(
                    content=[TextContent(type="text", text="No organizations found.")]
                )
            
            org_list = []
            for org in data:
                org_info = f"**{org['name']}** (ID: {org['id']})"
                if org.get('description'):
                    org_info += f"\n  - {org['description']}"
                org_info += f"\n  - Created: {org.get('created_at', 'Unknown')}"
                org_list.append(org_info)
            
            result = f"Found {len(data)} organization(s):\n\n" + "\n\n".join(org_list)
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to list organizations: {str(e)}")]
            )
    
    async def _list_teams(self, organization_id: Optional[str]) -> CallToolResult:
        """List teams, optionally filtered by organization"""
        try:
            params = {}
            if organization_id:
                params["organization_id"] = organization_id
            
            data = await self.api_client.get("/teams", params=params)
            
            if not data:
                filter_text = f" in organization {organization_id}" if organization_id else ""
                return CallToolResult(
                    content=[TextContent(type="text", text=f"No teams found{filter_text}.")]
                )
            
            team_list = []
            for team in data:
                team_info = f"**{team['name']}** (ID: {team['id']})"
                if team.get('description'):
                    team_info += f"\n  - {team['description']}"
                team_info += f"\n  - Type: {team.get('team_type', 'Unknown')}"
                team_info += f"\n  - Organization: {team.get('organization_id', 'Unknown')}"
                team_list.append(team_info)
            
            filter_text = f" in organization {organization_id}" if organization_id else ""
            result = f"Found {len(data)} team(s){filter_text}:\n\n" + "\n\n".join(team_list)
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to list teams: {str(e)}")]
            )
    
    async def _list_agents(self, team_id: Optional[str], skills: Optional[List[str]]) -> CallToolResult:
        """List agents with optional filtering"""
        try:
            params = {}
            if team_id:
                params["team_id"] = team_id
            
            data = await self.api_client.get("/agents", params=params)
            
            if not data:
                filter_text = f" in team {team_id}" if team_id else ""
                return CallToolResult(
                    content=[TextContent(type="text", text=f"No agents found{filter_text}.")]
                )
            
            # Filter by skills if provided
            if skills:
                filtered_agents = []
                for agent in data:
                    agent_skills = agent.get('config', {}).get('skills', [])
                    if any(skill.lower() in [s.lower() for s in agent_skills] for skill in skills):
                        filtered_agents.append(agent)
                data = filtered_agents
            
            if not data:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"No agents found matching the specified criteria.")]
                )
            
            agent_list = []
            for agent in data:
                agent_info = f"**{agent['name']}** (ID: {agent['id']})"
                agent_info += f"\n  - Role: {agent.get('role', 'Unknown')}"
                agent_info += f"\n  - Type: {agent.get('type', 'Unknown')}"
                agent_info += f"\n  - Team: {agent.get('team_id', 'Unknown')}"
                
                if agent.get('config'):
                    config = agent['config']
                    if config.get('skills'):
                        agent_info += f"\n  - Skills: {', '.join(config['skills'])}"
                    if config.get('tools'):
                        agent_info += f"\n  - Tools: {', '.join(config['tools'])}"
                
                agent_list.append(agent_info)
            
            filter_parts = []
            if team_id:
                filter_parts.append(f"team {team_id}")
            if skills:
                filter_parts.append(f"skills: {', '.join(skills)}")
            
            filter_text = f" matching {' and '.join(filter_parts)}" if filter_parts else ""
            result = f"Found {len(data)} agent(s){filter_text}:\n\n" + "\n\n".join(agent_list)
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to list agents: {str(e)}")]
            )
    
    async def _get_agent_details(self, agent_id: str) -> CallToolResult:
        """Get detailed information about a specific agent"""
        try:
            data = await self.api_client.get(f"/agents/{agent_id}")
            
            result = f"**Agent Details: {data['name']}**\n\n"
            result += f"- **ID**: {data['id']}\n"
            result += f"- **Role**: {data.get('role', 'Unknown')}\n"
            result += f"- **Type**: {data.get('type', 'Unknown')}\n"
            result += f"- **Team ID**: {data.get('team_id', 'Unknown')}\n"
            result += f"- **Status**: {data.get('status', 'Unknown')}\n"
            result += f"- **Created**: {data.get('created_at', 'Unknown')}\n"
            
            if data.get('config'):
                config = data['config']
                result += f"\n**Configuration:**\n"
                
                if config.get('goal'):
                    result += f"- **Goal**: {config['goal']}\n"
                if config.get('backstory'):
                    result += f"- **Backstory**: {config['backstory'][:200]}{'...' if len(config.get('backstory', '')) > 200 else ''}\n"
                if config.get('model'):
                    result += f"- **Model**: {config['model']}\n"
                if config.get('temperature'):
                    result += f"- **Temperature**: {config['temperature']}\n"
                if config.get('skills'):
                    result += f"- **Skills**: {', '.join(config['skills'])}\n"
                if config.get('tools'):
                    result += f"- **Tools**: {', '.join(config['tools'])}\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to get agent details: {str(e)}")]
            )
    
    async def _assign_task(self, task_data: Dict[str, Any]) -> CallToolResult:
        """Assign a task to an agent"""
        try:
            agent_id = task_data["agent_id"]
            
            # Prepare task payload
            payload = {
                "title": task_data["title"],
                "description": task_data["description"],
                "created_by": task_data.get("created_by", "claude-mcp-client"),
                "priority": task_data.get("priority", 5)
            }
            
            # Assign task to agent
            result = await self.api_client.post(f"/agents/{agent_id}/tasks", payload)
            
            response = f"✅ **Task Assigned Successfully**\n\n"
            response += f"- **Task ID**: {result.get('task_id', 'Unknown')}\n"
            response += f"- **Agent ID**: {agent_id}\n"
            response += f"- **Title**: {task_data['title']}\n"
            response += f"- **Priority**: {payload['priority']}\n"
            response += f"- **Status**: {result.get('status', 'assigned')}\n"
            response += f"\nThe task has been queued and will be processed by the agent."
            
            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to assign task: {str(e)}")]
            )
    
    async def _get_agent_templates(self, category: Optional[str]) -> CallToolResult:
        """List available agent templates"""
        try:
            data = await self.api_client.get("/templates")
            
            templates = data.get("templates", [])
            categories = data.get("categories", [])
            
            if category:
                templates = [t for t in templates if t.get("category") == category]
            
            if not templates:
                filter_text = f" in category '{category}'" if category else ""
                return CallToolResult(
                    content=[TextContent(type="text", text=f"No agent templates found{filter_text}.")]
                )
            
            result = f"**Available Agent Templates**\n\n"
            
            if not category:
                result += f"**Categories**: {', '.join(categories)}\n\n"
            
            # Group templates by category
            by_category = {}
            for template in templates:
                cat = template.get("category", "uncategorized")
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(template)
            
            for cat, cat_templates in by_category.items():
                result += f"### {cat.replace('_', ' ').title()}\n\n"
                
                for template in cat_templates:
                    result += f"**{template['name']}** (`{template['template_id']}`)\n"
                    result += f"- {template.get('description', 'No description')}\n"
                    
                    if template.get('skills'):
                        result += f"- **Skills**: {', '.join(template['skills'])}\n"
                    if template.get('tools'):
                        result += f"- **Tools**: {', '.join(template['tools'])}\n"
                    if template.get('default_model'):
                        result += f"- **Model**: {template['default_model']}\n"
                    
                    result += "\n"
                
                result += "\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to get agent templates: {str(e)}")]
            )
    
    async def _get_team_hierarchy(self, organization_id: Optional[str]) -> CallToolResult:
        """Get hierarchical view of organization → teams → agents"""
        try:
            # Get organizations
            orgs = await self.api_client.get("/organizations")
            if organization_id:
                orgs = [org for org in orgs if org['id'] == organization_id]
            
            if not orgs:
                return CallToolResult(
                    content=[TextContent(type="text", text="No organizations found.")]
                )
            
            result = "**Team Hierarchy**\n\n"
            
            for org in orgs:
                result += f"🏢 **{org['name']}** ({org['id']})\n"
                if org.get('description'):
                    result += f"   {org['description']}\n"
                
                # Get teams for this organization
                teams = await self.api_client.get("/teams", {"organization_id": org['id']})
                
                if not teams:
                    result += "   └── No teams found\n\n"
                    continue
                
                for i, team in enumerate(teams):
                    is_last_team = i == len(teams) - 1
                    team_prefix = "└──" if is_last_team else "├──"
                    
                    result += f"   {team_prefix} 👥 **{team['name']}** ({team['id']})\n"
                    if team.get('description'):
                        result += f"   {'    ' if is_last_team else '│   '}   {team['description']}\n"
                    
                    # Get agents for this team
                    agents = await self.api_client.get("/agents", {"team_id": team['id']})
                    
                    if not agents:
                        result += f"   {'    ' if is_last_team else '│   '}└── No agents\n"
                        continue
                    
                    for j, agent in enumerate(agents):
                        is_last_agent = j == len(agents) - 1
                        agent_prefix = "└──" if is_last_agent else "├──"
                        
                        result += f"   {'    ' if is_last_team else '│   '}{agent_prefix} 🤖 **{agent['name']}** ({agent.get('role', 'Unknown role')})\n"
                        
                        # Show agent skills if available
                        if agent.get('config', {}).get('skills'):
                            skills = ', '.join(agent['config']['skills'][:3])  # Show first 3 skills
                            if len(agent['config']['skills']) > 3:
                                skills += f" +{len(agent['config']['skills']) - 3} more"
                            result += f"   {'    ' if is_last_team else '│   '}{'    ' if is_last_agent else '│   '}   Skills: {skills}\n"
                
                result += "\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to get team hierarchy: {str(e)}")]
            )
    
    async def _deploy_agent(self, deploy_data: Dict[str, Any]) -> CallToolResult:
        """Deploy a new agent from a template"""
        try:
            payload = {
                "template_id": deploy_data["template_id"],
                "overrides": {
                    "name": deploy_data["name"],
                    "description": deploy_data.get("description"),
                    "team_id": deploy_data["team_id"],
                    **deploy_data.get("overrides", {})
                }
            }
            
            result = await self.api_client.post("/agents/from-template", payload)
            
            response = f"✅ **Agent Deployed Successfully**\n\n"
            response += f"- **Agent ID**: {result.get('id', 'Unknown')}\n"
            response += f"- **Name**: {deploy_data['name']}\n"
            response += f"- **Template**: {deploy_data['template_id']}\n"
            response += f"- **Team ID**: {deploy_data['team_id']}\n"
            response += f"- **Type**: {result.get('type', 'Unknown')}\n"
            response += f"- **Status**: {result.get('status', 'active')}\n"
            
            if result.get('config', {}).get('skills'):
                skills = ', '.join(result['config']['skills'][:5])
                if len(result['config']['skills']) > 5:
                    skills += f" +{len(result['config']['skills']) - 5} more"
                response += f"- **Skills**: {skills}\n"
            
            response += f"\nThe agent is now ready to receive tasks!"
            
            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to deploy agent: {str(e)}")]
            )
    
    async def _create_custom_agent(self, agent_data: Dict[str, Any]) -> CallToolResult:
        """Create a custom agent with specific configuration"""
        try:
            payload = {
                "team_id": agent_data["team_id"],
                "name": agent_data["name"],
                "role": agent_data["role"],
                "type": agent_data["type"],
                "description": agent_data.get("description"),
                "config": agent_data.get("config", {})
            }
            
            # Set defaults for config if not provided
            if "model" not in payload["config"]:
                payload["config"]["model"] = "claude-3-sonnet-20241022"
            if "temperature" not in payload["config"]:
                payload["config"]["temperature"] = 0.7
            if "max_tokens" not in payload["config"]:
                payload["config"]["max_tokens"] = 4096
            
            result = await self.api_client.post("/agents", payload)
            
            response = f"✅ **Custom Agent Created Successfully**\n\n"
            response += f"- **Agent ID**: {result.get('id', 'Unknown')}\n"
            response += f"- **Name**: {agent_data['name']}\n"
            response += f"- **Role**: {agent_data['role']}\n"
            response += f"- **Type**: {agent_data['type']}\n"
            response += f"- **Team ID**: {agent_data['team_id']}\n"
            response += f"- **Model**: {payload['config']['model']}\n"
            response += f"- **Temperature**: {payload['config']['temperature']}\n"
            
            if payload["config"].get("skills"):
                response += f"- **Skills**: {', '.join(payload['config']['skills'])}\n"
            if payload["config"].get("tools"):
                response += f"- **Tools**: {', '.join(payload['config']['tools'])}\n"
            
            response += f"\nThe custom agent is now ready for task assignments!"
            
            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to create custom agent: {str(e)}")]
            )
    
    async def _get_agent_tasks(self, agent_id: str, status: Optional[str] = None) -> CallToolResult:
        """Get tasks assigned to a specific agent"""
        try:
            params = {}
            if status:
                params["status"] = status
            
            tasks = await self.api_client.get(f"/agents/{agent_id}/tasks", params)
            
            if not tasks:
                status_filter = f" with status '{status}'" if status else ""
                return CallToolResult(
                    content=[TextContent(type="text", text=f"No tasks found for agent {agent_id}{status_filter}.")]
                )
            
            result = f"**Tasks for Agent {agent_id}**\n\n"
            
            if status:
                result += f"*Filtered by status: {status}*\n\n"
            
            # Group tasks by status
            by_status = {}
            for task in tasks:
                task_status = task.get("status", "unknown")
                if task_status not in by_status:
                    by_status[task_status] = []
                by_status[task_status].append(task)
            
            for task_status, status_tasks in by_status.items():
                status_emoji = {
                    "pending": "⏳",
                    "running": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                    "cancelled": "🚫"
                }.get(task_status, "❓")
                
                result += f"### {status_emoji} {task_status.title()} ({len(status_tasks)})\n\n"
                
                for task in status_tasks:
                    result += f"**{task.get('title', 'Untitled Task')}** (`{task.get('id', 'Unknown ID')}`)\n"
                    if task.get('description'):
                        result += f"- {task['description']}\n"
                    if task.get('priority'):
                        result += f"- Priority: {task['priority']}/10\n"
                    if task.get('created_at'):
                        result += f"- Created: {task['created_at']}\n"
                    if task.get('result'):
                        result += f"- Result: {task['result'][:100]}{'...' if len(task['result']) > 100 else ''}\n"
                    result += "\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to get agent tasks: {str(e)}")]
            )
    
    async def _update_task_status(self, update_data: Dict[str, Any]) -> CallToolResult:
        """Update the status of a specific task"""
        try:
            task_id = update_data["task_id"]
            new_status = update_data["status"]
            result = update_data.get("result")
            
            payload = {
                "status": new_status
            }
            if result:
                payload["result"] = result
            
            updated_task = await self.api_client.put(f"/tasks/{task_id}", payload)
            
            response = f"✅ **Task Status Updated**\n\n"
            response += f"- **Task ID**: {task_id}\n"
            response += f"- **New Status**: {new_status}\n"
            response += f"- **Title**: {updated_task.get('title', 'Unknown')}\n"
            
            if result:
                response += f"- **Result**: {result[:200]}{'...' if len(result) > 200 else ''}\n"
            
            if updated_task.get('updated_at'):
                response += f"- **Updated**: {updated_task['updated_at']}\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to update task status: {str(e)}")]
            )
    
    # Goals Management Methods
    
    async def _create_organizational_goal(self, goal_data: Dict[str, Any]) -> CallToolResult:
        """Create a new organizational goal"""
        try:
            organization_id = goal_data["organization_id"]
            
            # Prepare goal payload
            payload = {
                "title": goal_data["title"],
                "description": goal_data["description"],
                "goal_type": goal_data["goal_type"],
                "target_deadline": goal_data["target_deadline"],
                "priority_level": goal_data.get("priority_level", 5)
            }
            
            # Optional fields
            if "target_value" in goal_data:
                payload["target_value"] = goal_data["target_value"]
            if "target_unit" in goal_data:
                payload["target_unit"] = goal_data["target_unit"]
            if "assigned_teams" in goal_data:
                payload["assigned_teams"] = goal_data["assigned_teams"]
            if "tags" in goal_data:
                payload["tags"] = goal_data["tags"]
            
            result = await self.api_client.post(f"/organizations/{organization_id}/goals", payload)
            
            response = f"🎯 **Goal Created Successfully**\n\n"
            response += f"- **Goal ID**: {result.get('goal_id', 'Unknown')}\n"
            response += f"- **Organization**: {organization_id}\n"
            response += f"- **Title**: {goal_data['title']}\n"
            response += f"- **Type**: {goal_data['goal_type']}\n"
            response += f"- **Priority**: {payload['priority_level']}/10\n"
            response += f"- **Deadline**: {goal_data['target_deadline']}\n"
            
            if "target_value" in goal_data and "target_unit" in goal_data:
                response += f"- **Target**: {goal_data['target_value']} {goal_data['target_unit']}\n"
            
            if "assigned_teams" in goal_data:
                response += f"- **Teams**: {', '.join(goal_data['assigned_teams'])}\n"
            
            response += f"\nThe goal is now active and ready for milestone planning."
            
            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to create goal: {str(e)}")]
            )
    
    async def _list_organization_goals(self, filter_data: Dict[str, Any]) -> CallToolResult:
        """List goals for an organization"""
        try:
            organization_id = filter_data["organization_id"]
            
            # Build query parameters
            params = {}
            if "status" in filter_data:
                params["status"] = filter_data["status"]
            if "goal_type" in filter_data:
                params["goal_type"] = filter_data["goal_type"]
            if "limit" in filter_data:
                params["limit"] = filter_data["limit"]
            
            data = await self.api_client.get(f"/organizations/{organization_id}/goals", params)
            
            goals = data.get("goals", [])
            if not goals:
                filter_text = ""
                if params:
                    filter_parts = []
                    if "status" in params:
                        filter_parts.append(f"status: {', '.join(params['status'])}")
                    if "goal_type" in params:
                        filter_parts.append(f"type: {', '.join(params['goal_type'])}")
                    if filter_parts:
                        filter_text = f" matching {' and '.join(filter_parts)}"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=f"No goals found for organization {organization_id}{filter_text}.")]
                )
            
            result = f"🎯 **Goals for Organization {organization_id}**\n\n"
            result += f"Found {len(goals)} goal(s):\n\n"
            
            # Group goals by status
            by_status = {}
            for goal in goals:
                status = goal.get("status", "unknown")
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(goal)
            
            for status, status_goals in by_status.items():
                status_emoji = {
                    "active": "🟢",
                    "paused": "🟡",
                    "completed": "✅",
                    "cancelled": "🔴"
                }.get(status, "❓")
                
                result += f"### {status_emoji} {status.title()} ({len(status_goals)})\n\n"
                
                for goal in status_goals:
                    result += f"**{goal.get('title', 'Untitled Goal')}** (`{goal.get('id', 'Unknown ID')}`)\n"
                    result += f"- Type: {goal.get('goal_type', 'Unknown').title()}\n"
                    result += f"- Priority: {goal.get('priority_level', 'Unknown')}/10\n"
                    
                    if goal.get('progress_percentage') is not None:
                        result += f"- Progress: {goal['progress_percentage']:.1f}%\n"
                    
                    if goal.get('target_deadline'):
                        result += f"- Deadline: {goal['target_deadline']}\n"
                    
                    if goal.get('target_value') and goal.get('target_unit'):
                        result += f"- Target: {goal['target_value']} {goal['target_unit']}\n"
                        
                        if goal.get('current_value') is not None:
                            result += f"- Current: {goal['current_value']} {goal['target_unit']}\n"
                    
                    result += "\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to list goals: {str(e)}")]
            )
    
    async def _get_goal_details(self, goal_id: str) -> CallToolResult:
        """Get detailed information about a specific goal"""
        try:
            goal = await self.api_client.get(f"/goals/{goal_id}")
            
            result = f"🎯 **Goal Details: {goal.get('title', 'Unknown Title')}**\n\n"
            result += f"- **ID**: {goal.get('id', 'Unknown')}\n"
            result += f"- **Organization**: {goal.get('organization_id', 'Unknown')}\n"
            result += f"- **Type**: {goal.get('goal_type', 'Unknown').title()}\n"
            result += f"- **Status**: {goal.get('status', 'Unknown').title()}\n"
            result += f"- **Priority**: {goal.get('priority_level', 'Unknown')}/10\n"
            
            if goal.get('description'):
                result += f"- **Description**: {goal['description']}\n"
            
            # Progress Information
            if goal.get('progress_percentage') is not None:
                result += f"\n**Progress:**\n"
                result += f"- **Percentage**: {goal['progress_percentage']:.1f}%\n"
                
                if goal.get('current_value') is not None and goal.get('target_value') is not None:
                    result += f"- **Current**: {goal['current_value']} {goal.get('target_unit', '')}\n"
                    result += f"- **Target**: {goal['target_value']} {goal.get('target_unit', '')}\n"
                
                if goal.get('completion_confidence') is not None:
                    result += f"- **Confidence**: {goal['completion_confidence']*100:.0f}%\n"
            
            # Timeline Information
            result += f"\n**Timeline:**\n"
            if goal.get('start_date'):
                result += f"- **Start Date**: {goal['start_date']}\n"
            if goal.get('target_deadline'):
                result += f"- **Target Deadline**: {goal['target_deadline']}\n"
            if goal.get('actual_completion_date'):
                result += f"- **Completed**: {goal['actual_completion_date']}\n"
            
            # Team Assignment
            if goal.get('assigned_teams'):
                result += f"\n**Assigned Teams**: {', '.join(goal['assigned_teams'])}\n"
            
            # Tags
            if goal.get('tags'):
                result += f"**Tags**: {', '.join(goal['tags'])}\n"
            
            # Success Criteria
            if goal.get('success_criteria'):
                result += f"\n**Success Criteria**: {goal['success_criteria']}\n"
            
            # Timestamps
            result += f"\n**Created**: {goal.get('created_at', 'Unknown')}\n"
            result += f"**Updated**: {goal.get('updated_at', 'Unknown')}\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to get goal details: {str(e)}")]
            )
    
    async def _update_goal_progress(self, update_data: Dict[str, Any]) -> CallToolResult:
        """Update goal progress"""
        try:
            goal_id = update_data["goal_id"]
            
            # Prepare update payload
            payload = {}
            if "progress_percentage" in update_data:
                payload["progress_percentage"] = update_data["progress_percentage"]
            if "current_value" in update_data:
                payload["current_value"] = update_data["current_value"]
            if "completion_confidence" in update_data:
                payload["completion_confidence"] = update_data["completion_confidence"]
            if "notes" in update_data:
                payload["notes"] = update_data["notes"]
            
            result = await self.api_client.put(f"/goals/{goal_id}/progress", payload)
            
            response = f"📊 **Goal Progress Updated**\n\n"
            response += f"- **Goal ID**: {goal_id}\n"
            response += f"- **Status**: {result.get('status', 'updated')}\n"
            
            if "previous_progress" in result and "current_progress" in result:
                response += f"- **Progress Change**: {result['previous_progress']:.1f}% → {result['current_progress']:.1f}%\n"
            
            if "progress_percentage" in update_data:
                response += f"- **Current Progress**: {update_data['progress_percentage']:.1f}%\n"
            
            if "current_value" in update_data:
                response += f"- **Current Value**: {update_data['current_value']}\n"
            
            if "completion_confidence" in update_data:
                response += f"- **Confidence**: {update_data['completion_confidence']*100:.0f}%\n"
            
            if "notes" in update_data:
                response += f"- **Notes**: {update_data['notes'][:100]}{'...' if len(update_data['notes']) > 100 else ''}\n"
            
            response += f"\n**Updated**: {result.get('updated_at', 'Just now')}"
            
            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to update goal progress: {str(e)}")]
            )
    
    async def _generate_goal_execution_plan(self, plan_data: Dict[str, Any]) -> CallToolResult:
        """Generate execution plan for a goal"""
        try:
            goal_id = plan_data["goal_id"]
            
            # Prepare payload
            payload = {}
            if "planning_context" in plan_data:
                payload["planning_context"] = plan_data["planning_context"]
            
            result = await self.api_client.post(f"/goals/{goal_id}/generate-execution-plan", payload)
            
            response = f"📋 **Execution Plan Generated**\n\n"
            response += f"- **Goal ID**: {result.get('goal_id', goal_id)}\n"
            response += f"- **Plan Type**: {result.get('plan_type', 'Standard')}\n"
            
            if "summary" in result:
                summary = result["summary"]
                response += f"\n**Plan Summary:**\n"
                response += f"- **Total Milestones**: {summary.get('total_milestones', 0)}\n"
                response += f"- **Total Tasks**: {summary.get('total_tasks', 0)}\n"
                
                if "estimated_total_hours" in summary:
                    response += f"- **Estimated Hours**: {summary['estimated_total_hours']}\n"
                
                if "cross_functional_areas" in summary:
                    response += f"- **Functions**: {', '.join(summary['cross_functional_areas'])}\n"
            
            if "milestones" in result and result["milestones"]:
                response += f"\n**Generated Milestones:**\n"
                
                for i, milestone in enumerate(result["milestones"][:3], 1):  # Show first 3
                    response += f"{i}. **{milestone.get('title', f'Milestone {i}')}**\n"
                    if milestone.get('target_date'):
                        response += f"   - Target: {milestone['target_date']}\n"
                    if milestone.get('tasks'):
                        response += f"   - Tasks: {len(milestone['tasks'])}\n"
                
                if len(result["milestones"]) > 3:
                    response += f"... and {len(result['milestones']) - 3} more milestones\n"
            
            response += f"\nThe execution plan has been generated and milestones are ready for task creation."
            
            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to generate execution plan: {str(e)}")]
            )
    
    async def _create_goal_conversation(self, conv_data: Dict[str, Any]) -> CallToolResult:
        """Create a goal conversation"""
        try:
            goal_id = conv_data["goal_id"]
            
            payload = {
                "conversation_type": conv_data["conversation_type"],
                "conversation_title": conv_data["conversation_title"]
            }
            
            if "initial_context" in conv_data:
                payload["initial_context"] = conv_data["initial_context"]
            
            result = await self.api_client.post(f"/goals/{goal_id}/conversations", payload)
            
            response = f"💬 **Goal Conversation Created**\n\n"
            response += f"- **Conversation ID**: {result.get('conversation_id', 'Unknown')}\n"
            response += f"- **Goal ID**: {goal_id}\n"
            response += f"- **Type**: {conv_data['conversation_type'].title()}\n"
            response += f"- **Title**: {conv_data['conversation_title']}\n"
            response += f"- **Status**: {result.get('status', 'created')}\n"
            
            response += f"\nThe conversation is now active and ready for strategic planning discussions."
            
            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to create goal conversation: {str(e)}")]
            )
    
    async def _track_goal_progress(self, track_data: Dict[str, Any]) -> CallToolResult:
        """Track goal progress with risk assessment"""
        try:
            goal_id = track_data["goal_id"]
            
            payload = {
                "progress_percentage": track_data["progress_percentage"]
            }
            
            # Optional fields
            if "current_value" in track_data:
                payload["current_value"] = track_data["current_value"]
            if "notes" in track_data:
                payload["notes"] = track_data["notes"]
            if "confidence_score" in track_data:
                payload["confidence_score"] = track_data["confidence_score"]
            if "trigger_alerts" in track_data:
                payload["trigger_alerts"] = track_data["trigger_alerts"]
            
            result = await self.api_client.post(f"/goals/{goal_id}/track-progress", payload)
            
            response = f"📈 **Goal Progress Tracked**\n\n"
            response += f"- **Goal ID**: {goal_id}\n"
            response += f"- **Snapshot ID**: {result.get('snapshot_id', 'Unknown')}\n"
            response += f"- **Progress**: {track_data['progress_percentage']:.1f}%\n"
            
            if "current_value" in track_data:
                response += f"- **Current Value**: {track_data['current_value']}\n"
            
            if "confidence_score" in track_data:
                response += f"- **Confidence**: {track_data['confidence_score']*100:.0f}%\n"
            
            # Risk Assessment Results
            if "risk_assessment" in result:
                risk = result["risk_assessment"]
                response += f"\n**Risk Assessment:**\n"
                response += f"- **Risk Level**: {risk.get('risk_level', 'Unknown').title()}\n"
                response += f"- **Delay Probability**: {risk.get('probability_of_delay', 0)*100:.0f}%\n"
            
            if "progress_velocity" in result:
                response += f"- **Progress Velocity**: {result['progress_velocity']:.2f}\n"
            
            if "notes" in track_data:
                response += f"\n**Notes**: {track_data['notes'][:150]}{'...' if len(track_data['notes']) > 150 else ''}\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to track goal progress: {str(e)}")]
            )
    
    async def _assess_goal_deadline_risk(self, goal_id: str) -> CallToolResult:
        """Assess deadline risk for a goal"""
        try:
            result = await self.api_client.get(f"/goals/{goal_id}/deadline-risk")
            
            response = f"⚠️ **Goal Deadline Risk Assessment**\n\n"
            response += f"- **Goal ID**: {goal_id}\n"
            response += f"- **Risk Level**: {result.get('risk_level', 'Unknown').title()}\n"
            response += f"- **Delay Probability**: {result.get('probability_of_delay', 0)*100:.0f}%\n"
            
            if result.get('estimated_completion_date'):
                response += f"- **Estimated Completion**: {result['estimated_completion_date']}\n"
            
            if result.get('days_at_risk'):
                response += f"- **Days At Risk**: {result['days_at_risk']}\n"
            
            # Critical Path Items
            if result.get('critical_path_items'):
                response += f"\n**Critical Path Issues:**\n"
                for item in result['critical_path_items'][:3]:  # Show first 3
                    response += f"- {item.get('type', 'Unknown').replace('_', ' ').title()}: {item.get('title', 'Unknown')}\n"
                    if item.get('days_overdue'):
                        response += f"  (Overdue by {item['days_overdue']} days)\n"
                
                if len(result['critical_path_items']) > 3:
                    response += f"... and {len(result['critical_path_items']) - 3} more issues\n"
            
            # Mitigation Strategies
            if result.get('mitigation_strategies'):
                response += f"\n**Recommended Actions:**\n"
                for strategy in result['mitigation_strategies'][:2]:  # Show first 2
                    response += f"- **{strategy.get('strategy', 'Unknown').replace('_', ' ').title()}**: {strategy.get('description', 'No description')}\n"
                    if strategy.get('impact'):
                        response += f"  Expected impact: {strategy['impact'].replace('_', ' ')}\n"
            
            response += f"\n**Assessment Updated**: {result.get('updated_at', 'Just now')}"
            
            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to assess deadline risk: {str(e)}")]
            )
    
    async def _get_organization_goals_dashboard(self, organization_id: str) -> CallToolResult:
        """Get organization goals dashboard"""
        try:
            result = await self.api_client.get(f"/organizations/{organization_id}/goals-dashboard")
            
            response = f"📊 **Goals Dashboard - {organization_id}**\n\n"
            
            # Summary Statistics
            if "summary_statistics" in result:
                stats = result["summary_statistics"]
                response += f"**Overview:**\n"
                response += f"- **Total Goals**: {stats.get('total_goals', 0)}\n"
                response += f"- **Active**: {stats.get('active_goals', 0)}\n"
                response += f"- **Completed**: {stats.get('completed_goals', 0)}\n"
                response += f"- **Paused**: {stats.get('paused_goals', 0)}\n"
                if stats.get('cancelled_goals', 0) > 0:
                    response += f"- **Cancelled**: {stats['cancelled_goals']}\n"
            
            # Progress Overview
            if "progress_overview" in result:
                progress = result["progress_overview"]
                response += f"\n**Progress Overview:**\n"
                response += f"- **Average Progress**: {progress.get('average_progress', 0):.1f}%\n"
                response += f"- **Goals On Track**: {progress.get('goals_on_track', 0)}\n"
                response += f"- **Goals At Risk**: {progress.get('goals_at_risk', 0)}\n"
                
                if progress.get('total_target_value') and progress.get('total_current_value'):
                    response += f"- **Total Progress**: {progress['total_current_value']:.0f} / {progress['total_target_value']:.0f}\n"
            
            # Upcoming Deadlines
            if result.get('upcoming_deadlines'):
                response += f"\n**Upcoming Deadlines:**\n"
                for deadline in result['upcoming_deadlines'][:3]:  # Show first 3
                    response += f"- **{deadline.get('title', 'Unknown Goal')}**: {deadline.get('deadline')} ({deadline.get('days_remaining', '?')} days)\n"
                    response += f"  Progress: {deadline.get('progress', 0):.1f}%\n"
                
                if len(result['upcoming_deadlines']) > 3:
                    response += f"... and {len(result['upcoming_deadlines']) - 3} more deadlines\n"
            
            # High Priority Goals
            if result.get('high_priority_goals'):
                response += f"\n**High Priority Goals:**\n"
                for goal in result['high_priority_goals'][:3]:  # Show first 3
                    response += f"- **{goal.get('title', 'Unknown')}** (Priority: {goal.get('priority_level', '?')}/10)\n"
                    response += f"  Progress: {goal.get('progress', 0):.1f}%"
                    if goal.get('risk_level'):
                        response += f", Risk: {goal['risk_level'].title()}"
                    response += "\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to get goals dashboard: {str(e)}")]
            )
    
    async def run_stdio(self):
        """Run the MCP server with stdio transport"""
        logger.info("Starting MCP server with stdio transport")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, 
                write_stream, 
                self.server.create_initialization_options()
            )
    
    async def run_sse(self, host: str = "localhost", port: int = 8001):
        """Run the MCP server with SSE transport"""
        logger.info("Starting MCP server with SSE transport", host=host, port=port)
        
        # Create a simple health endpoint
        from aiohttp import web, web_runner
        import asyncio
        
        async def health_check(request):
            """Health check endpoint"""
            try:
                # Test connection to FuzeAgent API
                response = await self.api_client.get("/organizations")
                org_count = len(response) if isinstance(response, list) else 0
                return web.json_response({
                    "status": "healthy", 
                    "api_connection": "ok",
                    "mcp_tools": 20,  # Updated to include Goals management tools
                    "server_type": "sse",
                    "organizations_count": org_count
                })
            except Exception as e:
                return web.json_response({
                    "status": "unhealthy", 
                    "api_connection": "failed", 
                    "error": str(e)
                }, status=503)
        
        # Create web app for health check
        app = web.Application()
        app.router.add_get('/health', health_check)
        
        # Start health check server
        runner = web_runner.AppRunner(app)
        await runner.setup()
        site = web_runner.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"Health endpoint available at http://{host}:{port}/health")
        
        # Keep the server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down MCP SSE server")
        finally:
            await runner.cleanup()
    
    async def run(self, transport: str = "stdio", host: str = "localhost", port: int = 8001):
        """Run the MCP server with specified transport"""
        if transport.lower() == "sse":
            await self.run_sse(host, port)
        else:
            await self.run_stdio()

async def main():
    """Main entry point"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="FuzeAgent MCP Server")
    parser.add_argument(
        "--transport", 
        choices=["stdio", "sse"], 
        default="stdio",
        help="Transport mode: stdio for Claude Desktop, sse for web clients"
    )
    parser.add_argument(
        "--host", 
        default="localhost", 
        help="Host for SSE server (default: localhost)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8001, 
        help="Port for SSE server (default: 8001)"
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="FuzeAgent API URL (overrides FUZEAGENT_API_URL env var)"
    )
    
    args = parser.parse_args()
    
    # Get API URL from command line or environment variable
    api_url = args.api_url or os.getenv("FUZEAGENT_API_URL", "http://localhost:8000")
    
    logger.info(
        "Starting FuzeAgent MCP Server", 
        api_url=api_url, 
        transport=args.transport,
        host=args.host,
        port=args.port
    )
    
    # Create and run server
    server = FuzeAgentMCPServer(api_url)
    try:
        await server.run(transport=args.transport, host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server error", error=str(e))
        raise
    finally:
        await server.api_client.close()

if __name__ == "__main__":
    asyncio.run(main())