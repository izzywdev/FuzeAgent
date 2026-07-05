#!/bin/bash
set -e

echo "🚀 Starting FuzeAgent Orchestrator v2.0.0 (Autonomous Execution)"

# Function to wait for service to be ready using Python
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    
    echo "⏳ Waiting for $service_name to be ready at $host:$port..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if python -c "import socket; sock = socket.socket(); sock.settimeout(1); result = sock.connect_ex(('$host', $port)); sock.close(); exit(result)" 2>/dev/null; then
            break
        fi
        sleep 1
        timeout=$((timeout-1))
    done
    
    if [ $timeout -eq 0 ]; then
        echo "❌ Timeout waiting for $service_name"
        exit 1
    fi
    echo "✅ $service_name is ready!"
}

# Wait for database (host comes from DATABASE_URL to avoid hardcoding service name)
DB_HOST=$(echo "${DATABASE_URL:-postgresql://postgres:postgres@postgres:5432/ai_context}" | sed -E "s|.*@([^:/]+).*|\1|")
wait_for_service "$DB_HOST" 5432 "PostgreSQL"

# Wait for Redis
wait_for_service redis 6379 "Redis"

# Wait for RabbitMQ
wait_for_service rabbitmq 5672 "RabbitMQ"

# Initialize database schema if needed
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "📊 Running database migrations..."
    
    # Run basic schema setup
    python -c "
import asyncio
import asyncpg
import os
import sys

async def setup_database():
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print('❌ DATABASE_URL not set')
            sys.exit(1)
            
        conn = await asyncpg.connect(database_url)
        
        # Create extensions
        await conn.execute('CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";')
        await conn.execute('CREATE EXTENSION IF NOT EXISTS vector;')
        
        # Run model configuration schema
        schema_file = '/app/database_schema_models.sql'
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema = f.read()
            await conn.execute(schema)
            print('✅ Model configuration schema applied')
        
        await conn.close()
        print('✅ Database initialization complete')
        
    except Exception as e:
        print(f'❌ Database initialization failed: {e}')
        sys.exit(1)

asyncio.run(setup_database())
"
fi

# Set up Claude CLI authentication if API key is provided
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "🔐 Configuring Claude CLI authentication..."
    echo "Setting up Claude CLI with provided API key..."
    # Note: In production, this would use proper Claude CLI auth setup
fi

# Create necessary directories
echo "📁 Creating workspace directories..."
mkdir -p /app/workspaces
mkdir -p /app/.fuzeagent/backups
mkdir -p /tmp/fuzeagent

# Set permissions
chmod 755 /app/workspaces
chmod 755 /app/.fuzeagent/backups

# Generate encryption key if not provided
if [ -z "$ENCRYPTION_KEY" ]; then
    echo "🔐 Generating encryption key for API credentials..."
    export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
fi

# Log configuration
echo "⚙️  Configuration:"
echo "  - Autonomous Execution: ${ENABLE_AUTONOMOUS_EXECUTION:-true}"
echo "  - Multi-Agent Coordination: ${ENABLE_MULTI_AGENT_COORDINATION:-true}"
echo "  - File Operations: ${ENABLE_FILE_OPERATIONS:-true}"
echo "  - MCP Integration: ${ENABLE_MCP_INTEGRATION:-true}"
echo "  - Max Concurrent Executions: ${MAX_CONCURRENT_EXECUTIONS:-10}"
echo "  - Max Coordination Sessions: ${MAX_COORDINATION_SESSIONS:-5}"
echo "  - Claude CLI Path: ${CLAUDE_CLI_PATH:-/usr/local/bin/claude}"

# Check Claude CLI installation
if command -v claude >/dev/null 2>&1; then
    echo "✅ Claude CLI is installed: $(claude --version 2>/dev/null || echo 'version check failed')"
else
    echo "⚠️  Claude CLI not found - autonomous execution may be limited"
fi

# Check Docker access
if [ -S "/var/run/docker.sock" ]; then
    echo "✅ Docker socket is available for sandbox management"
else
    echo "⚠️  Docker socket not available - sandbox features may be limited"
fi

# Start the application
echo "🎯 Starting FuzeAgent Orchestrator with autonomous execution..."

exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --access-log \
    --use-colors \
    --log-level info