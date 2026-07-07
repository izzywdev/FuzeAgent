import asyncpg
import os
from fastapi import APIRouter, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Optional
import json
import httpx
import asyncio

from auth import authenticate_websocket
from database import DatabaseManager

router = APIRouter(prefix="/hierarchy", tags=["hierarchy"])


@router.get("/visualization")
async def get_hierarchy_visualization():
    """
    Get complete organizational hierarchy for visualization with ReactFlow/GoJS

    Returns structured data optimized for hierarchical visualization libraries:
    - Organizations as root nodes
    - Teams as intermediate nodes
    - Agents as leaf nodes
    - Relationships and positioning data
    """
    try:
        # Get data from hierarchy API
        async with httpx.AsyncClient() as client:
            # Get all organizations
            orgs_response = await client.get("http://localhost:8006/organizations")
            organizations = orgs_response.json()

            # Get all teams
            teams_response = await client.get("http://localhost:8006/teams")
            all_teams = teams_response.json()

            # Get all agents
            agents_response = await client.get("http://localhost:8006/agents")
            all_agents = agents_response.json()

        if not organizations:
            return {"nodes": [], "edges": [], "message": "No organizations found"}

        nodes = []
        edges = []
        y_offset = 0

        for org_idx, org in enumerate(organizations):
            org_id = org["id"]
            org_node_id = f"org-{org_id}"

            # Add organization node
            nodes.append(
                {
                    "id": org_node_id,
                    "type": "organization",
                    "data": {
                        "label": org["name"],
                        "description": org.get("description", ""),
                        "type": "Organization",
                        "settings": org.get("settings", {}),
                        "entity_id": org_id,
                    },
                    "position": {"x": org_idx * 800, "y": y_offset},
                    "style": {
                        "background": "#1e40af",
                        "color": "white",
                        "border": "2px solid #1e3a8a",
                        "borderRadius": "12px",
                        "padding": "12px",
                        "minWidth": "200px",
                    },
                }
            )

            # Filter teams for this organization
            teams = [t for t in all_teams if t.get("organization_id") == org_id]
            team_y_offset = y_offset + 150

            for team_idx, team in enumerate(teams):
                team_id = team["id"]
                team_node_id = f"team-{team_id}"

                # Add team node
                nodes.append(
                    {
                        "id": team_node_id,
                        "type": "team",
                        "data": {
                            "label": team["name"],
                            "description": team.get("description", ""),
                            "type": f"Team ({team.get('team_type', 'general')})",
                            "settings": team.get("settings", {}),
                            "entity_id": team_id,
                            "organization_id": org_id,
                        },
                        "position": {
                            "x": org_idx * 800 + (team_idx % 3) * 250 - 250,
                            "y": team_y_offset + (team_idx // 3) * 120,
                        },
                        "style": {
                            "background": "#059669",
                            "color": "white",
                            "border": "2px solid #047857",
                            "borderRadius": "8px",
                            "padding": "10px",
                            "minWidth": "180px",
                        },
                    }
                )

                # Add edge from organization to team
                edges.append(
                    {
                        "id": f"edge-{org_node_id}-{team_node_id}",
                        "source": org_node_id,
                        "target": team_node_id,
                        "type": "smoothstep",
                        "style": {"stroke": "#64748b", "strokeWidth": 2},
                        "markerEnd": {"type": "arrowclosed", "color": "#64748b"},
                    }
                )

                # Filter agents for this team - note: need to check team_id in agents
                agents = [
                    a
                    for a in all_agents
                    if a.get("team_id") == team_id
                    or (hasattr(a, "config") and a.config.get("team_id") == team_id)
                ]
                # Fallback: if no team_id in agent data, we'll have limited agents
                if not agents and all_agents:
                    # For now, include some agents if they don't have team assignments
                    agents = all_agents[:2]  # Include first 2 agents as examples

                agent_y_offset = team_y_offset + (team_idx // 3) * 120 + 100

                for agent_idx, agent in enumerate(agents):
                    agent_id = agent["id"]
                    agent_node_id = f"agent-{agent_id}"

                    # Determine agent color by type
                    agent_colors = {
                        "executive": {"bg": "#dc2626", "border": "#b91c1c"},
                        "developer": {"bg": "#2563eb", "border": "#1d4ed8"},
                        "marketing": {"bg": "#7c3aed", "border": "#6d28d9"},
                        "sales": {"bg": "#ea580c", "border": "#c2410c"},
                        "qa": {"bg": "#16a34a", "border": "#15803d"},
                        "devops": {"bg": "#0891b2", "border": "#0e7490"},
                        "designer": {"bg": "#e11d48", "border": "#be185d"},
                    }

                    agent_type = agent.get("type", "developer")
                    colors = agent_colors.get(
                        agent_type, {"bg": "#6b7280", "border": "#4b5563"}
                    )

                    # Add agent node
                    nodes.append(
                        {
                            "id": agent_node_id,
                            "type": "agent",
                            "data": {
                                "label": agent["name"],
                                "role": agent.get("role", ""),
                                "type": f"Agent ({agent_type})",
                                "status": agent.get("status", "active"),
                                "config": agent.get("config", {}),
                                "entity_id": agent_id,
                                "team_id": team_id,
                                "organization_id": org_id,
                            },
                            "position": {
                                "x": org_idx * 800
                                + (team_idx % 3) * 250
                                - 250
                                + (agent_idx % 2) * 120
                                - 60,
                                "y": agent_y_offset + (agent_idx // 2) * 80,
                            },
                            "style": {
                                "background": colors["bg"],
                                "color": "white",
                                "border": f"2px solid {colors['border']}",
                                "borderRadius": "6px",
                                "padding": "8px",
                                "minWidth": "150px",
                            },
                        }
                    )

                    # Add edge from team to agent
                    edges.append(
                        {
                            "id": f"edge-{team_node_id}-{agent_node_id}",
                            "source": team_node_id,
                            "target": agent_node_id,
                            "type": "smoothstep",
                            "style": {"stroke": "#94a3b8", "strokeWidth": 1.5},
                            "markerEnd": {"type": "arrowclosed", "color": "#94a3b8"},
                        }
                    )

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_organizations": len(organizations),
                "total_teams": len(all_teams),
                "total_agents": len(all_agents),
                "generated_at": "2025-08-06T10:00:00Z",
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate hierarchy visualization: {str(e)}",
        )


@router.get("/stats")
async def get_hierarchy_stats():
    """Get comprehensive hierarchy statistics"""
    try:
        organizations = await DatabaseManager.get_organizations()

        if not organizations:
            return {"organizations": 0, "teams": 0, "agents": 0, "by_organization": []}

        stats = {
            "organizations": len(organizations),
            "teams": 0,
            "agents": 0,
            "by_organization": [],
            "agent_types": {},
            "team_types": {},
        }

        for org in organizations:
            org_id = org["id"]
            teams = await DatabaseManager.get_teams(org_id)
            org_agent_count = 0
            org_teams_by_type = {}
            org_agents_by_type = {}

            for team in teams:
                team_id = team["id"]
                team_type = team.get("team_type", "general")
                org_teams_by_type[team_type] = org_teams_by_type.get(team_type, 0) + 1
                stats["team_types"][team_type] = (
                    stats["team_types"].get(team_type, 0) + 1
                )

                agents = await DatabaseManager.get_agents(team_id)
                org_agent_count += len(agents)

                for agent in agents:
                    agent_type = agent.get("type", "developer")
                    org_agents_by_type[agent_type] = (
                        org_agents_by_type.get(agent_type, 0) + 1
                    )
                    stats["agent_types"][agent_type] = (
                        stats["agent_types"].get(agent_type, 0) + 1
                    )

            stats["by_organization"].append(
                {
                    "id": org_id,
                    "name": org["name"],
                    "teams": len(teams),
                    "agents": org_agent_count,
                    "teams_by_type": org_teams_by_type,
                    "agents_by_type": org_agents_by_type,
                }
            )

            stats["teams"] += len(teams)
            stats["agents"] += org_agent_count

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get hierarchy stats: {str(e)}"
        )


@router.get("/organization/{organization_id}/chart")
async def get_organization_chart(organization_id: str):
    """Get detailed chart data for a specific organization"""
    try:
        # Get organization details
        organization = await DatabaseManager.get_organization(organization_id)
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Get teams and agents
        teams = await DatabaseManager.get_teams(organization_id)

        chart_data = {"organization": organization, "teams": [], "total_agents": 0}

        for team in teams:
            team_id = team["id"]
            agents = await DatabaseManager.get_agents(team_id)

            team_data = {
                "id": team_id,
                "name": team["name"],
                "description": team.get("description", ""),
                "team_type": team.get("team_type", "general"),
                "settings": team.get("settings", {}),
                "agents": agents,
                "agent_count": len(agents),
            }

            chart_data["teams"].append(team_data)
            chart_data["total_agents"] += len(agents)

        return chart_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get organization chart: {str(e)}"
        )


@router.get("/search")
async def search_hierarchy(q: str, entity_type: Optional[str] = None):
    """Search across organizations, teams, and agents"""
    try:
        if not q or len(q) < 2:
            raise HTTPException(
                status_code=400, detail="Query must be at least 2 characters"
            )

        results = {"organizations": [], "teams": [], "agents": [], "total_results": 0}

        query = q.lower()

        # Search organizations
        if not entity_type or entity_type == "organization":
            organizations = await DatabaseManager.get_organizations()
            for org in organizations:
                if (
                    query in org["name"].lower()
                    or query in org.get("description", "").lower()
                ):
                    results["organizations"].append(org)

        # Search teams
        if not entity_type or entity_type == "team":
            organizations = await DatabaseManager.get_organizations()
            for org in organizations:
                teams = await DatabaseManager.get_teams(org["id"])
                for team in teams:
                    if (
                        query in team["name"].lower()
                        or query in team.get("description", "").lower()
                        or query in team.get("team_type", "").lower()
                    ):
                        team["organization_name"] = org["name"]
                        results["teams"].append(team)

        # Search agents
        if not entity_type or entity_type == "agent":
            organizations = await DatabaseManager.get_organizations()
            for org in organizations:
                teams = await DatabaseManager.get_teams(org["id"])
                for team in teams:
                    agents = await DatabaseManager.get_agents(team["id"])
                    for agent in agents:
                        if (
                            query in agent["name"].lower()
                            or query in agent.get("role", "").lower()
                            or query in agent.get("type", "").lower()
                        ):
                            agent["organization_name"] = org["name"]
                            agent["team_name"] = team["name"]
                            results["agents"].append(agent)

        results["total_results"] = (
            len(results["organizations"])
            + len(results["teams"])
            + len(results["agents"])
        )

        return results

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ---------------------------------------------------------------------------
# Standalone FastAPI app — used when hierarchy_endpoints is run as its own
# service (hierarchy-api, port 8006).  Mounts the router above and adds a
# /ws WebSocket endpoint with connect-time JWT auth.
# ---------------------------------------------------------------------------

app = FastAPI(title="FuzeAgent Hierarchy API")
app.include_router(router)


@app.on_event("startup")
async def _pool_startup() -> None:
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:password@postgres:5432/ai_context"
    )
    app.state.pool = await asyncpg.create_pool(database_url)


@app.on_event("shutdown")
async def _pool_shutdown() -> None:
    if hasattr(app.state, "pool"):
        await app.state.pool.close()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Real-time hierarchy stream. Auth via query-param, subprotocol, or header."""
    user = await authenticate_websocket(websocket)
    if user is None:
        return
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
