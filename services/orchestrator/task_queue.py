import asyncio
import aio_pika
import json
import os
from typing import Dict, List, Optional, Any
from database import DatabaseManager

class TaskQueue:
    def __init__(self):
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://admin:password@rabbitmq:5672/")
        self.connection = None
        self.channel = None
        self.task_execution_engine = None  # Will be set by orchestrator
        
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
    
    async def start_autonomous_execution(self, task_id: str) -> Dict[str, Any]:
        """Start autonomous execution of a task"""
        if not self.task_execution_engine:
            raise RuntimeError("TaskExecutionEngine not configured")
            
        return await self.task_execution_engine.start_task_execution(task_id)
    
    async def get_execution_status(self, task_id: str) -> Dict[str, Any]:
        """Get execution status of a task"""
        if not self.task_execution_engine:
            raise RuntimeError("TaskExecutionEngine not configured")
            
        return await self.task_execution_engine.get_execution_status(task_id)
    
    async def get_task_iterations(self, task_id: str) -> List[Dict[str, Any]]:
        """Get task iteration history"""
        if not self.task_execution_engine:
            raise RuntimeError("TaskExecutionEngine not configured")
            
        return await self.task_execution_engine.get_task_iterations(task_id)
    
    async def handle_human_response(self, task_id: str, response: str) -> bool:
        """Handle human response to a task question"""
        if not self.task_execution_engine:
            raise RuntimeError("TaskExecutionEngine not configured")
            
        return await self.task_execution_engine.handle_human_response(task_id, response)
    
    async def cancel_task_execution(self, task_id: str) -> bool:
        """Cancel autonomous execution of a task"""
        if not self.task_execution_engine:
            raise RuntimeError("TaskExecutionEngine not configured")
            
        return await self.task_execution_engine.cancel_task_execution(task_id)
    
    def set_task_execution_engine(self, engine):
        """Set the task execution engine reference"""
        self.task_execution_engine = engine
    
    async def close(self):
        """Close RabbitMQ connection"""
        if self.connection:
            await self.connection.close()