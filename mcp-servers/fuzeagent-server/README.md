# FuzeAgent MCP Server

A Model Context Protocol (MCP) server that exposes FuzeAgent organizations, teams, and agents as tools for Claude Desktop integration.

## Features

- **Organization Management**: List and query organizations
- **Team Operations**: Access team information and structure
- **Agent Discovery**: Find and interact with specialized agents
- **Task Assignment**: Delegate tasks to appropriate agents
- **Real-time Status**: Monitor agent availability and workload

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a configuration file for Claude Desktop:

```json
{
  "mcpServers": {
    "fuzeagent": {
      "command": "python",
      "args": ["/path/to/fuzeagent-server/server.py"],
      "env": {
        "FUZEAGENT_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

## Available Tools

### 1. list_organizations
List all available organizations in the FuzeAgent system.

### 2. list_teams
List teams within a specific organization or all teams.

### 3. list_agents
Discover available agents, optionally filtered by team or skills.

### 4. get_agent_details
Get detailed information about a specific agent including capabilities and current status.

### 5. assign_task
Assign a task to a specific agent with context and requirements.

### 6. get_agent_templates
List available agent templates for creating new specialized agents.

## Usage Examples

Once integrated with Claude Desktop, you can use natural language to:

- "Show me all the development teams in my organization"
- "List all Python developers available for a new project"
- "Assign a code review task to the senior developer agent"
- "What agent templates are available for QA work?"

## API Integration

The MCP server communicates with the FuzeAgent orchestrator API to:
- Fetch real-time data about organizations, teams, and agents
- Submit task assignments and monitor progress
- Retrieve agent capabilities and availability
- Access agent templates and configurations

This enables seamless integration between Claude Desktop and your FuzeAgent AI team infrastructure.