import httpx
import json
from typing import Dict, Any, List

class ContextClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_context(self, query: str, agent_id: str = None) -> Dict[str, Any]:
        """Get relevant context for a query"""
        try:
            params = {"query": query}
            if agent_id:
                params["agent_id"] = agent_id
                
            response = await self.client.get(f"{self.base_url}/context", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to get context: {e}")
            return {}
    
    async def store_interaction(self, agent_id: str, content: str, metadata: Dict = None) -> str:
        """Store agent interaction"""
        try:
            data = {
                "agent_id": agent_id,
                "content": content,
                "metadata": metadata or {}
            }
            response = await self.client.post(f"{self.base_url}/context/interactions", json=data)
            response.raise_for_status()
            result = response.json()
            return result.get("interaction_id", "")
        except Exception as e:
            print(f"Failed to store interaction: {e}")
            return ""
    
    async def update_task(self, task_id: str, status: str, result: Dict = None, error: str = None):
        """Update task status"""
        try:
            data = {"status": status}
            if result:
                data["result"] = result
            if error:
                data["error"] = error
                
            response = await self.client.put(f"{self.base_url}/tasks/{task_id}", json=data)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to update task: {e}")
    
    async def get_agent_memory(self, agent_id: str, limit: int = 10) -> List[Dict]:
        """Get agent's memory/interaction history"""
        try:
            params = {"limit": limit}
            response = await self.client.get(f"{self.base_url}/agents/{agent_id}/memory", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to get agent memory: {e}")
            return []
    
    async def search_knowledge(self, query: str, limit: int = 5) -> List[Dict]:
        """Search across all agent knowledge"""
        try:
            params = {"query": query, "limit": limit}
            response = await self.client.get(f"{self.base_url}/knowledge/search", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to search knowledge: {e}")
            return []
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()