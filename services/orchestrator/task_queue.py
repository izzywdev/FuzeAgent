import asyncio
import aio_pika
import json
import os
from typing import Dict, List
from .database import DatabaseManager

class TaskQueue:
    def __init__(self):
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://admin:password@rabbitmq:5672/")
        self.connection = None
        self.channel = None
        
    async def connect(self):
        """Connect to RabbitMQ"""
        if not self.connection:
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.channel = await self.connection.channel()
    
    async def assign_task(self, agent_id: str, task: dict) -> str:
        """Assign a task to an agent"""
        await self.connect()
        
        # Insert task into database
        task_id = await DatabaseManager.insert_task(
            title=task.get('title', 'Untitled Task'),
            description=task.get('description', ''),
            assigned_to=agent_id,
            created_by=task.get('created_by')
        )
        
        # Add task_id to task data
        task['id'] = task_id
        task['assigned_to'] = agent_id
        
        # Send task to agent's queue
        queue_name = f"agent_{agent_id.replace('-', '_')}"
        queue = await self.channel.declare_queue(queue_name, durable=True)
        
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                json.dumps(task).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue_name
        )
        
        return task_id
    
    async def list_tasks(self) -> List[Dict]:
        """List all tasks"""
        return await DatabaseManager.get_tasks()
    
    async def get_task(self, task_id: str) -> Dict:
        """Get specific task"""
        tasks = await self.list_tasks()
        for task in tasks:
            if str(task['id']) == task_id:
                return task
        return None
    
    async def update_task_status(self, task_id: str, status: str, result: dict = None):
        """Update task status"""
        await DatabaseManager.update_task_status(task_id, status, result)
    
    async def get_pending_tasks(self) -> List[Dict]:
        """Get all pending tasks"""
        tasks = await self.list_tasks()
        return [task for task in tasks if task['status'] == 'pending']
    
    async def get_agent_tasks(self, agent_id: str) -> List[Dict]:
        """Get tasks assigned to specific agent"""
        tasks = await self.list_tasks()
        return [task for task in tasks if str(task['assigned_to']) == agent_id]
    
    async def close(self):
        """Close RabbitMQ connection"""
        if self.connection:
            await self.connection.close()