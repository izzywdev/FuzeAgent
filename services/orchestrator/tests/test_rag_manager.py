"""
Test cases for RAG Manager functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from rag_manager import RAGManager


@pytest.mark.rag
@pytest.mark.database
@pytest.mark.asyncio
class TestRAGManager:
    """Test RAG Manager functionality"""

    @pytest.fixture
    async def rag_manager_with_mock_embedding(self, migration_manager):
        """RAG manager with mocked embedding model"""
        database_url = "postgresql://postgres:password@localhost:5434/ai_context_test"
        api_key = "test-api-key"

        with patch("rag_manager.SentenceTransformer") as mock_transformer:
            # Mock the embedding model
            mock_model = MagicMock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3] * 128]  # 384 dimensions
            mock_transformer.return_value = mock_model

            manager = RAGManager(database_url, api_key)
            await manager.initialize()

            yield manager
            await manager.close()

    async def test_initialize_creates_tables(self, rag_manager_with_mock_embedding):
        """Test that initialization creates required tables"""
        manager = rag_manager_with_mock_embedding

        # Check that tables exist by trying to query them
        async with manager.db_pool.acquire() as conn:
            # Check agent_conversations table
            result = await conn.fetchrow(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'agent_conversations'
                );
            """
            )
            assert result["exists"] is True

            # Check conversation_summaries table
            result = await conn.fetchrow(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'conversation_summaries'
                );
            """
            )
            assert result["exists"] is True

    async def test_store_conversation_message(
        self, rag_manager_with_mock_embedding, setup_test_data
    ):
        """Test storing conversation messages"""
        manager = rag_manager_with_mock_embedding
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        session_id = "test-session-123"
        message = "Hello, I need help with Python development"
        sender = "user"

        # Store message
        result = await manager.store_conversation_message(
            agent_id=agent_id, session_id=session_id, message=message, sender=sender
        )

        assert "message_id" in result
        assert result["session_id"] == session_id

        # Verify message was stored
        async with manager.db_pool.acquire() as conn:
            stored_message = await conn.fetchrow(
                """
                SELECT * FROM agent_conversations 
                WHERE agent_id = $1 AND session_id = $2
            """,
                agent_id,
                session_id,
            )

            assert stored_message is not None
            assert stored_message["message"] == message
            assert stored_message["sender"] == sender

    async def test_get_conversation_history(
        self, rag_manager_with_mock_embedding, setup_test_data
    ):
        """Test retrieving conversation history"""
        manager = rag_manager_with_mock_embedding
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]
        session_id = "test-session-456"

        # Store multiple messages
        messages = [
            ("user", "What is FastAPI?"),
            ("assistant", "FastAPI is a modern Python web framework"),
            ("user", "How do I create an API endpoint?"),
        ]

        for sender, message in messages:
            await manager.store_conversation_message(
                agent_id=agent_id, session_id=session_id, message=message, sender=sender
            )

        # Get conversation history
        history = await manager.get_conversation_history(agent_id, session_id)

        assert len(history) == 3
        assert history[0]["message"] == messages[0][1]  # Oldest first
        assert history[0]["sender"] == messages[0][0]
        assert history[-1]["message"] == messages[-1][1]  # Newest last

    async def test_get_conversation_history_with_limit(
        self, rag_manager_with_mock_embedding, setup_test_data
    ):
        """Test retrieving conversation history with limit"""
        manager = rag_manager_with_mock_embedding
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]
        session_id = "test-session-limit"

        # Store 5 messages
        for i in range(5):
            await manager.store_conversation_message(
                agent_id=agent_id,
                session_id=session_id,
                message=f"Message {i}",
                sender="user",
            )

        # Get only last 3 messages
        history = await manager.get_conversation_history(agent_id, session_id, limit=3)

        assert len(history) == 3
        assert history[-1]["message"] == "Message 4"  # Most recent
        assert history[0]["message"] == "Message 2"  # 3rd most recent

    @patch("rag_manager.ConversationSummaryBufferMemory")
    async def test_summarize_conversation(
        self, mock_memory_class, rag_manager_with_mock_embedding, setup_test_data
    ):
        """Test conversation summarization"""
        manager = rag_manager_with_mock_embedding
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]
        session_id = "test-session-summary"

        # Mock the conversation memory
        mock_memory = MagicMock()
        mock_memory.predict_new_summary.return_value = (
            "This is a test conversation summary"
        )
        mock_memory_class.return_value = mock_memory

        # Store some messages
        messages = [
            ("user", "Hello"),
            ("assistant", "Hi there!"),
            ("user", "How are you?"),
            ("assistant", "I'm doing well, thank you!"),
        ]

        for sender, message in messages:
            await manager.store_conversation_message(
                agent_id=agent_id, session_id=session_id, message=message, sender=sender
            )

        # Summarize conversation
        summary = await manager.summarize_conversation(agent_id, session_id)

        assert summary is not None
        assert "summary" in summary
        assert summary["summary"] == "This is a test conversation summary"

        # Verify summary was stored in database
        async with manager.db_pool.acquire() as conn:
            stored_summary = await conn.fetchrow(
                """
                SELECT * FROM conversation_summaries 
                WHERE agent_id = $1 AND session_id = $2
            """,
                agent_id,
                session_id,
            )

            assert stored_summary is not None
            assert stored_summary["summary"] == "This is a test conversation summary"

    async def test_store_agent_knowledge(
        self, rag_manager_with_mock_embedding, setup_test_data
    ):
        """Test storing agent knowledge with embeddings"""
        manager = rag_manager_with_mock_embedding
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        knowledge_item = {
            "title": "Python Best Practices",
            "content": "Always use type hints and follow PEP 8 standards for Python development",
            "category": "development",
            "tags": ["python", "best-practices", "pep8"],
        }

        # Store knowledge
        result = await manager.store_agent_knowledge(agent_id, knowledge_item)

        assert "knowledge_id" in result

        # Verify knowledge was stored with embedding
        async with manager.db_pool.acquire() as conn:
            stored_knowledge = await conn.fetchrow(
                """
                SELECT * FROM agent_knowledge_base 
                WHERE agent_id = $1 AND title = $2
            """,
                agent_id,
                knowledge_item["title"],
            )

            assert stored_knowledge is not None
            assert stored_knowledge["content"] == knowledge_item["content"]
            assert stored_knowledge["category"] == knowledge_item["category"]
            assert stored_knowledge["content_embedding"] is not None

    async def test_search_agent_knowledge(
        self, rag_manager_with_mock_embedding, setup_test_data
    ):
        """Test searching agent knowledge using semantic similarity"""
        manager = rag_manager_with_mock_embedding
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Store some knowledge items
        knowledge_items = [
            {
                "title": "Python Functions",
                "content": "Functions in Python are defined using the def keyword",
                "category": "python-basics",
            },
            {
                "title": "FastAPI Routing",
                "content": "FastAPI uses decorators to define API routes",
                "category": "web-development",
            },
            {
                "title": "Database Connections",
                "content": "Use connection pooling for better database performance",
                "category": "database",
            },
        ]

        for item in knowledge_items:
            await manager.store_agent_knowledge(agent_id, item)

        # Search for relevant knowledge
        search_results = await manager.search_agent_knowledge(
            agent_id=agent_id, query="How to create functions in Python?", limit=2
        )

        assert len(search_results) <= 2
        assert isinstance(search_results, list)

        # Results should have required fields
        for result in search_results:
            assert "title" in result
            assert "content" in result
            assert "similarity_score" in result

    async def test_get_enhanced_context(
        self, rag_manager_with_mock_embedding, setup_test_data
    ):
        """Test getting enhanced context for agent responses"""
        manager = rag_manager_with_mock_embedding
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]
        session_id = "test-context-session"

        # Store conversation history
        await manager.store_conversation_message(
            agent_id=agent_id,
            session_id=session_id,
            message="Tell me about Python",
            sender="user",
        )

        # Store relevant knowledge
        await manager.store_agent_knowledge(
            agent_id,
            {
                "title": "Python Overview",
                "content": "Python is a high-level programming language",
                "category": "programming",
            },
        )

        # Get enhanced context
        context = await manager.get_enhanced_context(
            agent_id=agent_id,
            session_id=session_id,
            current_query="What are Python's main features?",
        )

        assert "conversation_history" in context
        assert "relevant_knowledge" in context
        assert "session_summary" in context

        assert len(context["conversation_history"]) > 0
        assert isinstance(context["relevant_knowledge"], list)

    async def test_cleanup_old_conversations(
        self, rag_manager_with_mock_embedding, setup_test_data
    ):
        """Test cleaning up old conversation data"""
        manager = rag_manager_with_mock_embedding
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Store a message
        await manager.store_conversation_message(
            agent_id=agent_id,
            session_id="cleanup-test",
            message="Test message",
            sender="user",
        )

        # Cleanup conversations (with very short retention for testing)
        result = await manager.cleanup_old_conversations(retention_days=0)

        assert "deleted_conversations" in result
        assert "deleted_summaries" in result
        assert isinstance(result["deleted_conversations"], int)

    async def test_get_agent_statistics(
        self, rag_manager_with_mock_embedding, setup_test_data
    ):
        """Test getting agent conversation statistics"""
        manager = rag_manager_with_mock_embedding
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]
        session_id = "stats-test"

        # Store multiple messages
        for i in range(5):
            await manager.store_conversation_message(
                agent_id=agent_id,
                session_id=session_id,
                message=f"Message {i}",
                sender="user" if i % 2 == 0 else "assistant",
            )

        # Get statistics
        stats = await manager.get_agent_statistics(agent_id)

        assert "total_messages" in stats
        assert "total_sessions" in stats
        assert "knowledge_items" in stats
        assert stats["total_messages"] >= 5
        assert stats["total_sessions"] >= 1

    async def test_error_handling_invalid_agent(self, rag_manager_with_mock_embedding):
        """Test error handling with invalid agent ID"""
        manager = rag_manager_with_mock_embedding
        fake_agent_id = "550e8400-e29b-41d4-a716-446655440999"

        # Should handle gracefully without throwing exceptions
        history = await manager.get_conversation_history(fake_agent_id, "test-session")
        assert history == []

        knowledge = await manager.search_agent_knowledge(fake_agent_id, "test query")
        assert knowledge == []

    async def test_concurrent_operations(
        self, rag_manager_with_mock_embedding, setup_test_data
    ):
        """Test concurrent RAG operations"""
        import asyncio

        manager = rag_manager_with_mock_embedding
        test_data = await setup_test_data
        agent_id = test_data["agent_id"]

        # Create multiple concurrent operations
        tasks = []

        # Store messages concurrently
        for i in range(10):
            task = manager.store_conversation_message(
                agent_id=agent_id,
                session_id=f"concurrent-{i}",
                message=f"Concurrent message {i}",
                sender="user",
            )
            tasks.append(task)

        # Wait for all operations to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check that all operations succeeded
        for result in results:
            assert not isinstance(result, Exception)
            assert "message_id" in result
