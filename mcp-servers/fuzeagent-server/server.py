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
from mcp.server.sse import sse_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    GetPromptRequest,
    GetPromptResult,
    PromptMessage,
    GetResourceRequest,
    GetResourceResult,
    ListResourcesRequest,
    ListResourcesResult,
    Resource,
    Prompt
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
        
        # Add health check endpoint for SSE mode
        from aiohttp import web
        
        async def health_check(request):
            """Health check endpoint"""
            try:
                # Test connection to FuzeAgent API
                await self.api_client.get("/")
                return web.json_response({"status": "healthy", "api_connection": "ok"})
            except Exception as e:
                return web.json_response(
                    {"status": "unhealthy", "api_connection": "failed", "error": str(e)}, 
                    status=503
                )
        
        async def setup_health_routes(app):
            """Setup health check routes"""
            app.router.add_get('/health', health_check)
        
        async with sse_server(
            host=host, 
            port=port,
            setup_handlers=setup_health_routes
        ) as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
    
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