"""
Migration: Add RAG Chat History System
Created: 2025-01-29T14:00:01

This migration adds comprehensive chat history storage with vector embeddings
for RAG (Retrieval-Augmented Generation) functionality.
"""


async def upgrade(conn):
    """Apply the migration - Add RAG chat history tables"""

    # Agent Conversations Table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            session_id UUID NOT NULL,
            message_type VARCHAR(50) NOT NULL CHECK (message_type IN ('user', 'agent', 'system', 'tool')),
            content TEXT NOT NULL,
            embedding vector(1536),
            metadata JSONB DEFAULT '{}',
            parent_message_id UUID REFERENCES agent_conversations(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ Created agent_conversations table")

    # Conversation Summaries Table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation_summaries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            session_id UUID NOT NULL,
            summary_text TEXT NOT NULL,
            summary_embedding vector(1536),
            message_count INTEGER NOT NULL DEFAULT 0,
            token_count INTEGER DEFAULT 0,
            time_range TSTZRANGE,
            summary_type VARCHAR(50) DEFAULT 'auto' CHECK (summary_type IN ('auto', 'manual', 'periodic')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ Created conversation_summaries table")

    # Knowledge Base Table for RAG
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_knowledge_base (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            content_type VARCHAR(50) DEFAULT 'text' CHECK (content_type IN ('text', 'code', 'documentation', 'conversation')),
            source_type VARCHAR(50) DEFAULT 'manual' CHECK (source_type IN ('manual', 'conversation', 'task', 'upload')),
            source_reference UUID,  -- Reference to original source (task_id, conversation_id, etc.)
            embedding vector(1536),
            metadata JSONB DEFAULT '{}',
            tags TEXT[] DEFAULT ARRAY[]::TEXT[],
            relevance_score FLOAT DEFAULT 1.0,
            access_count INTEGER DEFAULT 0,
            last_accessed TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ Created agent_knowledge_base table")

    # Chat Sessions Table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            session_name VARCHAR(255),
            session_type VARCHAR(50) DEFAULT 'conversation' CHECK (session_type IN ('conversation', 'task', 'collaboration')),
            status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'archived')),
            participants JSONB DEFAULT '[]',  -- Array of participant IDs
            context JSONB DEFAULT '{}',
            message_count INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ Created chat_sessions table")

    # Create indexes for performance
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_agent_conversations_agent_session 
        ON agent_conversations(agent_id, session_id, created_at DESC);
    """)

    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_agent_conversations_embedding 
        ON agent_conversations USING ivfflat (embedding vector_cosine_ops);
    """)

    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversation_summaries_agent 
        ON conversation_summaries(agent_id, created_at DESC);
    """)

    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversation_summaries_embedding 
        ON conversation_summaries USING ivfflat (summary_embedding vector_cosine_ops);
    """)

    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_knowledge_base_agent 
        ON agent_knowledge_base(agent_id, content_type, created_at DESC);
    """)

    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding 
        ON agent_knowledge_base USING ivfflat (embedding vector_cosine_ops);
    """)

    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_knowledge_base_tags 
        ON agent_knowledge_base USING GIN(tags);
    """)

    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_sessions_agent 
        ON chat_sessions(agent_id, status, last_activity DESC);
    """)

    print("✅ Created performance indexes for RAG system")

    # Add triggers for automatic timestamp updates
    await conn.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    for table in [
        "agent_conversations",
        "conversation_summaries",
        "agent_knowledge_base",
        "chat_sessions",
    ]:
        await conn.execute(f"""
            DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
            CREATE TRIGGER update_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)

    print("✅ Created automatic timestamp update triggers")

    # Add foreign key constraint for session references
    await conn.execute("""
        ALTER TABLE agent_conversations 
        ADD CONSTRAINT fk_conversations_session 
        FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE;
    """)

    await conn.execute("""
        ALTER TABLE conversation_summaries 
        ADD CONSTRAINT fk_summaries_session 
        FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE;
    """)

    print("✅ Added foreign key constraints for session references")


async def downgrade(conn):
    """Rollback the migration - Remove RAG chat history tables"""

    # Drop tables in reverse order to handle foreign key constraints
    tables = [
        "agent_conversations",
        "conversation_summaries",
        "agent_knowledge_base",
        "chat_sessions",
    ]

    for table in tables:
        await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
        print(f"✅ Dropped {table} table")

    # Drop the trigger function
    await conn.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;")
    print("✅ Dropped timestamp update function")

    print("✅ RAG chat history system tables removed")
