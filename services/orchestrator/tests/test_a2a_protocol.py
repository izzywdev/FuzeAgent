"""
Test cases for A2A Protocol functionality
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from a2a_protocol import A2AProtocolManager, AgentCapability, TaskDelegation


@pytest.mark.a2a
@pytest.mark.database
@pytest.mark.asyncio
class TestA2AProtocol:
    """Test A2A Protocol functionality"""

    async def test_register_agent_capability(self, a2a_manager, setup_test_data):
        """Test registering agent capabilities"""
        manager = a2a_manager
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        capability = AgentCapability(
            capability_id="python_development",
            name="Python Development",
            description="Develop Python applications and scripts",
            input_schema={"type": "object", "properties": {"task": {"type": "string"}}},
            output_schema={
                "type": "object",
                "properties": {"result": {"type": "string"}},
            },
            metadata={"language": "python", "framework": "fastapi"},
        )

        result = await manager.register_agent_capability(agent_id, capability)

        assert result["success"] is True
        assert "capability_id" in result

        # Verify capability was stored
        stored_capability = await manager.get_agent_capability(agent_id, "python_development")
        assert stored_capability is not None
        assert stored_capability["name"] == capability.name

    async def test_discover_agents_by_capability(self, a2a_manager, setup_test_data):
        """Test discovering agents by capability"""
        manager = a2a_manager
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Register a capability
        capability = AgentCapability(
            capability_id="data_analysis",
            name="Data Analysis",
            description="Analyze datasets and generate insights",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

        await manager.register_agent_capability(agent_id, capability)

        # Discover agents with this capability
        agents = await manager.discover_agents_by_capability("data_analysis")

        assert len(agents) >= 1
        assert any(agent["agent_id"] == agent_id for agent in agents)

        # Check agent has the capability information
        found_agent = next(agent for agent in agents if agent["agent_id"] == agent_id)
        assert found_agent["capability_name"] == "Data Analysis"

    async def test_delegate_task_to_agent(self, a2a_manager, setup_test_data):
        """Test delegating task to another agent"""
        manager = a2a_manager
        test_data = await setup_test_data
        source_agent = test_data["agent_id"]
        target_agent = test_data["agent_id"]  # Using same agent for simplicity

        task_delegation = TaskDelegation(
            task_id="task-001",
            source_agent_id=source_agent,
            target_agent_id=target_agent,
            capability_required="python_development",
            task_data={
                "instruction": "Create a REST API endpoint",
                "requirements": ["FastAPI", "Pydantic", "PostgreSQL"],
            },
            priority=5,
            timeout_seconds=300,
        )

        result = await manager.delegate_task(task_delegation)

        assert result["success"] is True
        assert "delegation_id" in result
        assert result["status"] == "pending"

        # Verify delegation was stored
        delegation = await manager.get_task_delegation(result["delegation_id"])
        assert delegation is not None
        assert delegation["task_id"] == "task-001"
        assert delegation["source_agent_id"] == source_agent

    async def test_get_pending_delegations(self, a2a_manager, setup_test_data):
        """Test getting pending task delegations for an agent"""
        manager = a2a_manager
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Create multiple delegations
        for i in range(3):
            task_delegation = TaskDelegation(
                task_id=f"task-{i:03d}",
                source_agent_id=agent_id,
                target_agent_id=agent_id,
                capability_required="testing",
                task_data={"test_case": i},
                priority=i + 1,
            )
            await manager.delegate_task(task_delegation)

        # Get pending delegations
        pending = await manager.get_pending_delegations(agent_id)

        assert len(pending) >= 3

        # Should be ordered by priority (descending) then created_at
        priorities = [d["priority"] for d in pending]
        assert priorities == sorted(priorities, reverse=True)

    async def test_accept_task_delegation(self, a2a_manager, setup_test_data):
        """Test accepting a task delegation"""
        manager = a2a_manager
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Create delegation
        task_delegation = TaskDelegation(
            task_id="accept-test",
            source_agent_id=agent_id,
            target_agent_id=agent_id,
            capability_required="code_review",
            task_data={"code": "def hello(): return 'world'"},
        )

        delegation_result = await manager.delegate_task(task_delegation)
        delegation_id = delegation_result["delegation_id"]

        # Accept the delegation
        result = await manager.accept_task_delegation(delegation_id, agent_id)

        assert result["success"] is True
        assert result["status"] == "accepted"

        # Verify status was updated
        delegation = await manager.get_task_delegation(delegation_id)
        assert delegation["status"] == "accepted"
        assert delegation["accepted_at"] is not None

    async def test_complete_task_delegation(self, a2a_manager, setup_test_data):
        """Test completing a task delegation"""
        manager = a2a_manager
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Create and accept delegation
        task_delegation = TaskDelegation(
            task_id="complete-test",
            source_agent_id=agent_id,
            target_agent_id=agent_id,
            capability_required="documentation",
            task_data={"module": "user_management"},
        )

        delegation_result = await manager.delegate_task(task_delegation)
        delegation_id = delegation_result["delegation_id"]

        await manager.accept_task_delegation(delegation_id, agent_id)

        # Complete the delegation
        completion_data = {
            "result": "Documentation has been created",
            "artifacts": ["user_guide.md", "api_docs.json"],
            "execution_time": 120,
        }

        result = await manager.complete_task_delegation(delegation_id, completion_data)

        assert result["success"] is True
        assert result["status"] == "completed"

        # Verify completion data was stored
        delegation = await manager.get_task_delegation(delegation_id)
        assert delegation["status"] == "completed"
        assert delegation["result"] == completion_data["result"]
        assert delegation["completed_at"] is not None

    async def test_reject_task_delegation(self, a2a_manager, setup_test_data):
        """Test rejecting a task delegation"""
        manager = a2a_manager
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Create delegation
        task_delegation = TaskDelegation(
            task_id="reject-test",
            source_agent_id=agent_id,
            target_agent_id=agent_id,
            capability_required="impossible_task",
            task_data={"impossible": True},
        )

        delegation_result = await manager.delegate_task(task_delegation)
        delegation_id = delegation_result["delegation_id"]

        # Reject the delegation
        rejection_reason = "Task requirements are not feasible"
        result = await manager.reject_task_delegation(delegation_id, agent_id, rejection_reason)

        assert result["success"] is True
        assert result["status"] == "rejected"

        # Verify rejection was recorded
        delegation = await manager.get_task_delegation(delegation_id)
        assert delegation["status"] == "rejected"
        assert delegation["rejection_reason"] == rejection_reason

    async def test_get_agent_collaboration_history(self, a2a_manager, setup_test_data):
        """Test getting agent collaboration history"""
        manager = a2a_manager
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Create several delegations with different outcomes
        outcomes = ["completed", "rejected", "timeout"]

        for i, outcome in enumerate(outcomes):
            task_delegation = TaskDelegation(
                task_id=f"history-{i}",
                source_agent_id=agent_id,
                target_agent_id=agent_id,
                capability_required="test_capability",
                task_data={"test": i},
            )

            delegation_result = await manager.delegate_task(task_delegation)
            delegation_id = delegation_result["delegation_id"]

            if outcome == "completed":
                await manager.accept_task_delegation(delegation_id, agent_id)
                await manager.complete_task_delegation(delegation_id, {"result": f"Test {i} completed"})
            elif outcome == "rejected":
                await manager.reject_task_delegation(delegation_id, agent_id, "Test rejection")

        # Get collaboration history
        history = await manager.get_agent_collaboration_history(agent_id)

        assert len(history) >= 3

        # Verify different statuses are present
        statuses = {h["status"] for h in history}
        assert "completed" in statuses
        assert "rejected" in statuses
        assert "pending" in statuses  # timeout case still pending

    async def test_get_system_collaboration_metrics(self, a2a_manager, setup_test_data):
        """Test getting system-wide collaboration metrics"""
        manager = a2a_manager
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Create some delegations
        for i in range(5):
            task_delegation = TaskDelegation(
                task_id=f"metrics-{i}",
                source_agent_id=agent_id,
                target_agent_id=agent_id,
                capability_required="metrics_test",
                task_data={"test": i},
            )
            await manager.delegate_task(task_delegation)

        # Get system metrics
        metrics = await manager.get_system_collaboration_metrics()

        assert "total_delegations" in metrics
        assert "active_delegations" in metrics
        assert "completed_delegations" in metrics
        assert "average_completion_time" in metrics
        assert "most_requested_capabilities" in metrics

        assert metrics["total_delegations"] >= 5
        assert isinstance(metrics["most_requested_capabilities"], list)

    async def test_capability_matching(self, a2a_manager, setup_test_data):
        """Test capability matching algorithm"""
        manager = a2a_manager
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Register capabilities with different tags
        capabilities = [
            AgentCapability(
                capability_id="web_dev",
                name="Web Development",
                description="Build web applications",
                input_schema={},
                output_schema={},
                metadata={
                    "languages": ["python", "javascript"],
                    "frameworks": ["fastapi", "react"],
                },
            ),
            AgentCapability(
                capability_id="data_science",
                name="Data Science",
                description="Analyze data and build models",
                input_schema={},
                output_schema={},
                metadata={"languages": ["python", "r"], "tools": ["pandas", "sklearn"]},
            ),
        ]

        for cap in capabilities:
            await manager.register_agent_capability(agent_id, cap)

        # Test exact match
        exact_matches = await manager.discover_agents_by_capability("web_dev")
        assert len(exact_matches) >= 1

        # Test fuzzy matching by metadata
        python_agents = await manager.find_agents_by_metadata({"languages": ["python"]})
        assert len(python_agents) >= 1

    async def test_task_timeout_handling(self, a2a_manager, setup_test_data):
        """Test handling of task timeouts"""
        manager = a2a_manager
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Create delegation with short timeout
        task_delegation = TaskDelegation(
            task_id="timeout-test",
            source_agent_id=agent_id,
            target_agent_id=agent_id,
            capability_required="slow_task",
            task_data={"duration": 1000},
            timeout_seconds=1,  # Very short timeout
        )

        delegation_result = await manager.delegate_task(task_delegation)
        delegation_id = delegation_result["delegation_id"]

        # Accept but don't complete (simulate timeout)
        await manager.accept_task_delegation(delegation_id, agent_id)

        # Check for timed out tasks
        timed_out = await manager.check_and_handle_timeouts()

        assert len(timed_out) >= 1

        # Verify task was marked as timed out
        delegation = await manager.get_task_delegation(delegation_id)
        assert delegation["status"] == "timeout"

    async def test_inter_agent_messaging(self, a2a_manager, setup_test_data):
        """Test inter-agent messaging functionality"""
        manager = a2a_manager
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Send message between agents (using same agent for simplicity)
        message_data = {
            "subject": "Collaboration Request",
            "content": "I need help with database optimization",
            "message_type": "request",
            "metadata": {"priority": "high", "domain": "database"},
        }

        result = await manager.send_inter_agent_message(from_agent_id=agent_id, to_agent_id=agent_id, message_data=message_data)

        assert result["success"] is True
        assert "message_id" in result

        # Get messages for agent
        messages = await manager.get_agent_messages(agent_id)

        assert len(messages) >= 1
        sent_message = next(m for m in messages if m["message_id"] == result["message_id"])
        assert sent_message["subject"] == message_data["subject"]
        assert sent_message["message_type"] == message_data["message_type"]

    async def test_concurrent_delegations(self, a2a_manager, setup_test_data):
        """Test handling concurrent task delegations"""
        import asyncio

        manager = a2a_manager
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Create multiple concurrent delegations
        tasks = []
        for i in range(10):
            task_delegation = TaskDelegation(
                task_id=f"concurrent-{i}",
                source_agent_id=agent_id,
                target_agent_id=agent_id,
                capability_required="concurrent_test",
                task_data={"index": i},
            )
            tasks.append(manager.delegate_task(task_delegation))

        # Wait for all delegations to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all succeeded
        for result in results:
            assert not isinstance(result, Exception)
            assert result["success"] is True

        # Verify all were stored
        pending = await manager.get_pending_delegations(agent_id)
        concurrent_tasks = [d for d in pending if d["task_id"].startswith("concurrent-")]
        assert len(concurrent_tasks) == 10

    async def test_error_handling_invalid_agent(self, a2a_manager):
        """Test error handling with invalid agent IDs"""
        manager = a2a_manager
        fake_agent_id = "550e8400-e29b-41d4-a716-446655440999"

        # Should handle gracefully
        capabilities = await manager.get_agent_capabilities(fake_agent_id)
        assert capabilities == []

        pending = await manager.get_pending_delegations(fake_agent_id)
        assert pending == []

        history = await manager.get_agent_collaboration_history(fake_agent_id)
        assert history == []
