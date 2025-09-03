from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-templates", tags=["agent-templates"])

# Mock agent templates data
AGENT_TEMPLATES = [
    {
        "id": "dev-assistant",
        "template_id": "dev-assistant",
        "name": "Development Assistant",
        "description": "A helpful coding assistant for software development tasks",
        "category": "developer",
        "default_model": "claude-sonnet-4-20250514",
        "default_temperature": 0.7,
        "tools": ["code_analysis", "file_operations"],
        "default_goal": "Help with software development tasks",
        "default_backstory": "I am an AI assistant specialized in helping developers write better code and solve technical problems.",
        "default_docker_image": "python:3.11-slim"
    },
    {
        "id": "data-analyst",
        "template_id": "data-analyst",
        "name": "Data Analyst",
        "description": "Specialized in data analysis and visualization",
        "category": "analyst",
        "default_model": "claude-sonnet-4-20250514",
        "default_temperature": 0.5,
        "tools": ["data_analysis", "chart_generation"],
        "default_goal": "Analyze data and provide insights",
        "default_backstory": "I am an AI assistant focused on data analysis, statistical modeling, and creating visualizations.",
        "default_docker_image": "python:3.11-slim"
    },
    {
        "id": "project-manager",
        "template_id": "project-manager",
        "name": "Project Manager",
        "description": "Helps with project planning and task management",
        "category": "manager",
        "default_model": "claude-sonnet-4-20250514",
        "default_temperature": 0.6,
        "tools": ["task_management", "scheduling"],
        "default_goal": "Manage projects and coordinate team activities",
        "default_backstory": "I am an AI assistant designed to help with project management, task tracking, and team coordination.",
        "default_docker_image": "python:3.11-slim"
    }
]

@router.get("/", response_model=List[Dict[str, Any]])
async def get_agent_templates():
    """Get all available agent templates"""
    logger.info("GET /agent-templates - Retrieving all agent templates")
    return AGENT_TEMPLATES

@router.get("/{template_id}")
async def get_agent_template(template_id: str):
    """Get a specific agent template by ID"""
    logger.info(f"GET /agent-templates/{template_id} - Retrieving template")

    template = next((t for t in AGENT_TEMPLATES if t["id"] == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    return template
