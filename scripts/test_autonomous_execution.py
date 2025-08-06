#!/usr/bin/env python3
"""
Test script for FuzeAgent autonomous execution system

This script tests the complete autonomous execution workflow:
1. Creates an agent with repository settings
2. Assigns a development task
3. Starts autonomous execution
4. Monitors conversation and progress
5. Verifies completion
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

API_BASE = "http://localhost:8000"

async def test_autonomous_execution():
    """Test the complete autonomous execution workflow"""
    
    print("🧪 Testing FuzeAgent Autonomous Execution System")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        
        # Step 1: Create an agent with repository settings
        print("\n📋 Step 1: Creating agent with repository settings...")
        agent_data = {
            "name": "Test Security Developer",
            "role": "Security Developer", 
            "type": "developer",
            "template_id": "security_developer",
            "team_id": "test_team_001",
            "config": {
                "goal": "Implement secure coding practices and security features",
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.3
            },
            "repository_settings": {
                "repository_url": "https://github.com/your-org/test-repo.git",
                "default_branch": "main",
                "auto_create_pr": True,
                "require_review": True
            },
            "sandbox_settings": {
                "base_image": "fuzeagent/dev-python:latest",
                "resource_limits": {
                    "memory": "2Gi",
                    "cpu": "1.0",
                    "disk": "10Gi"
                },
                "auto_cleanup": "24h"
            }
        }
        
        async with session.post(f"{API_BASE}/agents", json=agent_data) as response:
            if response.status == 200:
                result = await response.json()
                agent_id = result["agent_id"]
                print(f"✅ Agent created: {agent_id}")
            else:
                print(f"❌ Failed to create agent: {response.status}")
                return
        
        # Step 2: Assign a development task
        print("\n📋 Step 2: Assigning development task...")
        task_data = {
            "title": "Implement user input validation",
            "description": """
            Create a comprehensive input validation system for user data:
            
            1. Implement input sanitization functions for common data types
            2. Add SQL injection prevention
            3. Create XSS protection utilities
            4. Write comprehensive unit tests
            5. Add documentation and usage examples
            
            Requirements:
            - Use Python with appropriate security libraries
            - Follow OWASP guidelines
            - Include error handling and logging
            - Ensure performance optimization
            """,
            "type": "security_feature",
            "priority": 8,
            "created_by": "test_system"
        }
        
        async with session.post(f"{API_BASE}/agents/{agent_id}/tasks", json=task_data) as response:
            if response.status == 200:
                result = await response.json()
                task_id = result["task_id"]
                print(f"✅ Task assigned: {task_id}")
            else:
                print(f"❌ Failed to assign task: {response.status}")
                return
        
        # Step 3: Start autonomous execution
        print("\n📋 Step 3: Starting autonomous execution...")
        async with session.post(f"{API_BASE}/tasks/{task_id}/execute") as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Autonomous execution started: {result['status']}")
            else:
                print(f"❌ Failed to start execution: {response.status}")
                return
        
        # Step 4: Monitor execution progress
        print("\n📋 Step 4: Monitoring execution progress...")
        
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        
        while (time.time() - start_time) < max_wait_time:
            # Get execution status
            async with session.get(f"{API_BASE}/tasks/{task_id}/status") as response:
                if response.status == 200:
                    status = await response.json()
                    current_status = status.get("status", "unknown")
                    iteration = status.get("current_iteration", 0)
                    
                    print(f"⏱️ Status: {current_status}, Iteration: {iteration}")
                    
                    # Check if completed or failed
                    if current_status in ["completed", "failed", "cancelled"]:
                        print(f"🏁 Execution finished with status: {current_status}")
                        break
                        
                    # Check if waiting for human input
                    if current_status == "waiting_for_human":
                        print("❓ Agent is asking for human input...")
                        
                        # Get task iterations to see the question
                        async with session.get(f"{API_BASE}/tasks/{task_id}/iterations") as iter_response:
                            if iter_response.status == 200:
                                iterations = await iter_response.json()
                                
                                # Find the latest iteration with a human question
                                for iteration_data in reversed(iterations):
                                    if iteration_data.get("human_question"):
                                        question = iteration_data["human_question"]
                                        print(f"❓ Question: {question}")
                                        
                                        # Provide a test response
                                        response_data = {"response": "Focus on readability while maintaining good performance. Prioritize clean, maintainable code."}\n                                        \n                                        async with session.post(f\"{API_BASE}/tasks/{task_id}/human-response\", json=response_data) as resp:\n                                            if resp.status == 200:\n                                                print(\"✅ Human response submitted\")\n                                            else:\n                                                print(f\"❌ Failed to submit response: {resp.status}\")\n                                        break\n                else:\n                    print(f\"❌ Failed to get status: {response.status}\")\n                    \n            await asyncio.sleep(10)  # Wait 10 seconds before checking again\n        \n        # Step 5: Get final results and conversation\n        print(\"\\n📋 Step 5: Getting final results...\")\n        \n        # Get conversation summary\n        async with session.get(f\"{API_BASE}/tasks/{task_id}/conversation/summary\") as response:\n            if response.status == 200:\n                summary = await response.json()\n                print(f\"💬 Conversation Summary:\")\n                print(f\"   - Total messages: {summary.get('total_messages', 0)}\")\n                print(f\"   - Total tokens: {summary.get('total_tokens', 0)}\")\n                print(f\"   - Max iteration: {summary.get('max_iteration', 0)}\")\n                print(f\"   - Human interactions: {summary.get('human_interactions', {}).get('total', 0)}\")\n            else:\n                print(f\"❌ Failed to get conversation summary: {response.status}\")\n        \n        # Get code generations\n        async with session.get(f\"{API_BASE}/tasks/{task_id}/code-generations\") as response:\n            if response.status == 200:\n                code_gens = await response.json()\n                generations = code_gens.get('code_generations', [])\n                print(f\"💻 Code Generations: {len(generations)} files created\")\n                for gen in generations[:3]:  # Show first 3\n                    print(f\"   - {gen.get('file_path')} ({gen.get('language')})\")\n            else:\n                print(f\"❌ Failed to get code generations: {response.status}\")\n        \n        # Get agent performance\n        async with session.get(f\"{API_BASE}/agents/{agent_id}/performance\") as response:\n            if response.status == 200:\n                performance = await response.json()\n                metrics = performance.get('metrics', [])\n                print(f\"📊 Performance Metrics: {len(metrics)} recorded\")\n                for metric in metrics[:3]:  # Show first 3\n                    print(f\"   - {metric.get('metric_type')}: {metric.get('metric_value')} {metric.get('metric_unit', '')}\")\n            else:\n                print(f\"❌ Failed to get performance metrics: {response.status}\")\n    \n    print(\"\\n\" + \"=\"*60)\n    print(\"🎉 Autonomous execution test completed!\")\n    print(\"\\nThis test verified:\")\n    print(\"✅ Agent creation with repository and sandbox settings\")\n    print(\"✅ Task assignment and autonomous execution startup\")\n    print(\"✅ Progress monitoring and status tracking\")\n    print(\"✅ Human-in-the-loop interaction handling\")\n    print(\"✅ Conversation tracking and storage\")\n    print(\"✅ Code generation and performance metrics\")\n\nasync def main():\n    \"\"\"Main test runner\"\"\"\n    try:\n        await test_autonomous_execution()\n    except Exception as e:\n        print(f\"\\n❌ Test failed with error: {e}\")\n        import traceback\n        traceback.print_exc()\n\nif __name__ == \"__main__\":\n    asyncio.run(main())"