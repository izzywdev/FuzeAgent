import asyncio
import aio_pika
import json
import os
from typing import Dict, Any
from abc import ABC, abstractmethod
from context_client import ContextClient

class BaseAgent(ABC):
    def __init__(self):
        self.name = os.environ.get('AGENT_NAME', 'Unknown Agent')
        self.role = os.environ.get('AGENT_ROLE', 'Generic Agent')
        self.type = os.environ.get('AGENT_TYPE', 'base')
        self.context_client = ContextClient(os.environ.get('CONTEXT_API_URL', 'http://orchestrator:8000'))
        self.rabbitmq_url = os.environ.get('RABBITMQ_URL', 'amqp://admin:password@rabbitmq:5672/')
        
    async def start(self):
        """Start listening for tasks"""
        print(f"Starting {self.name} ({self.role})")
        
        # Connect to RabbitMQ
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        
        async with connection:
            channel = await connection.channel()
            
            # Declare queue for this agent
            queue_name = f"agent_{self.name.lower().replace(' ', '_')}"
            queue = await channel.declare_queue(queue_name, durable=True)
            
            # Start consuming tasks
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        await self.process_task(json.loads(message.body))
    
    async def process_task(self, task: Dict[str, Any]):
        """Process a task"""
        task_id = task.get('id')
        task_type = task.get('type', 'unknown')
        
        print(f"{self.name} processing task {task_id}: {task.get('title', 'Untitled')}")
        
        try:
            # Get relevant context
            context = await self.context_client.get_context(
                query=task.get('description', ''),
                agent_id=self.name
            )
            
            # Execute task based on type
            result = await self.execute_task(task, context)
            
            # Update task status
            await self.context_client.update_task(
                task_id=task_id,
                status='completed',
                result=result
            )
            
            # Store interaction in context
            await self.context_client.store_interaction(
                agent_id=self.name,
                content=f"Completed task: {task.get('title', 'Untitled')}",
                metadata={
                    'task_id': task_id,
                    'task_type': task_type,
                    'result': result
                }
            )
            
            print(f"{self.name} completed task {task_id}")
            
        except Exception as e:
            print(f"{self.name} failed task {task_id}: {str(e)}")
            await self.context_client.update_task(
                task_id=task_id,
                status='failed',
                error=str(e)
            )
    
    @abstractmethod
    async def execute_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual task - to be implemented by subclasses"""
        pass

if __name__ == "__main__":
    # This is the base class - should not be run directly
    print("BaseAgent is an abstract class. Use a specific agent implementation.")
    import sys
    sys.exit(1)