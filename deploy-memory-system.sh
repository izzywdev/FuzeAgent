#!/bin/bash

# Deploy Memory-Enhanced Agent System
# This script sets up the complete persistent memory system for FuzeAgent

set -e  # Exit on any error

echo "🚀 Deploying FuzeAgent Memory-Enhanced Agent System"
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check required environment variables
check_env_vars() {
    echo -e "${BLUE}🔍 Checking environment variables...${NC}"
    
    required_vars=("DATABASE_URL" "ANTHROPIC_API_KEY")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo -e "${RED}❌ Missing required environment variables:${NC}"
        for var in "${missing_vars[@]}"; do
            echo -e "${RED}   - $var${NC}"
        done
        echo ""
        echo "Please set these variables and run the script again."
        echo "Example:"
        echo "export DATABASE_URL='postgresql://postgres:password@localhost:5434/ai_context'"
        echo "export ANTHROPIC_API_KEY='your-api-key-here'"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All required environment variables are set${NC}"
}

# Check if database is accessible
check_database() {
    echo -e "${BLUE}🔍 Checking database connection...${NC}"
    
    python3 -c "
import asyncpg
import asyncio
import os

async def test_connection():
    try:
        conn = await asyncpg.connect(os.environ['DATABASE_URL'])
        await conn.fetchval('SELECT 1')
        await conn.close()
        print('✅ Database connection successful')
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        exit(1)

asyncio.run(test_connection())
" || {
        echo -e "${RED}❌ Database connection failed. Please ensure the database is running and accessible.${NC}"
        exit 1
    }
}

# Run database migrations
run_migrations() {
    echo -e "${BLUE}🗄️ Running database migrations...${NC}"
    
    # Migration 003: Persistent agent memory schema
    echo -e "${YELLOW}   Running migration 003: Persistent agent memory schema${NC}"
    python3 -c "
import asyncpg
import asyncio
import os

async def run_migration():
    try:
        conn = await asyncpg.connect(os.environ['DATABASE_URL'])
        
        with open('services/orchestrator/migrations/003_add_persistent_agent_memory.sql', 'r') as f:
            migration_sql = f.read()
        
        await conn.execute(migration_sql)
        await conn.close()
        print('✅ Migration 003 completed successfully')
    except Exception as e:
        if 'already exists' in str(e):
            print('✅ Migration 003 already applied')
        else:
            print(f'❌ Migration 003 failed: {e}')
            exit(1)

asyncio.run(run_migration())
"

    # Migration 004: Tasks table updates
    echo -e "${YELLOW}   Running migration 004: Tasks table updates${NC}"
    python3 -c "
import asyncpg
import asyncio
import os

async def run_migration():
    try:
        conn = await asyncpg.connect(os.environ['DATABASE_URL'])
        
        with open('services/orchestrator/migrations/004_update_tasks_for_memory_agents.sql', 'r') as f:
            migration_sql = f.read()
        
        await conn.execute(migration_sql)
        await conn.close()
        print('✅ Migration 004 completed successfully')
    except Exception as e:
        if 'already exists' in str(e):
            print('✅ Migration 004 already applied')
        else:
            print(f'❌ Migration 004 failed: {e}')
            exit(1)

asyncio.run(run_migration())
"

    echo -e "${GREEN}✅ All database migrations completed${NC}"
}

# Build memory-enabled agent containers
build_containers() {
    echo -e "${BLUE}🐳 Building memory-enabled agent containers...${NC}"
    
    # Build base container
    echo -e "${YELLOW}   Building base development container${NC}"
    docker build -t fuzeagent/dev-base:latest ./containers/templates/dev-base/ || {
        echo -e "${RED}❌ Failed to build base container${NC}"
        exit 1
    }
    
    # Build Python development container
    echo -e "${YELLOW}   Building Python development container${NC}"
    docker build -t fuzeagent/dev-python:latest ./containers/templates/dev-python/ || {
        echo -e "${RED}❌ Failed to build Python container${NC}"
        exit 1
    }
    
    # Build TypeScript development container
    echo -e "${YELLOW}   Building TypeScript development container${NC}"
    docker build -t fuzeagent/dev-typescript:latest ./containers/templates/dev-typescript/ || {
        echo -e "${RED}❌ Failed to build TypeScript container${NC}"
        exit 1
    }
    
    # Build React development container
    echo -e "${YELLOW}   Building React development container${NC}"
    docker build -t fuzeagent/dev-react:latest ./containers/templates/dev-react/ || {
        echo -e "${RED}❌ Failed to build React container${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✅ All agent containers built successfully${NC}"
}

# Install Python dependencies for memory system
install_dependencies() {
    echo -e "${BLUE}📦 Installing memory system dependencies...${NC}"
    
    # Check if requirements are satisfied
    python3 -c "
import sys
try:
    import asyncpg
    import sentence_transformers
    import numpy
    import anthropic
    print('✅ All memory system dependencies are installed')
except ImportError as e:
    print(f'Installing missing dependency: {e.name}')
    sys.exit(1)
" || {
        echo -e "${YELLOW}   Installing missing dependencies...${NC}"
        pip3 install -r containers/templates/agent-process/requirements.txt
    }
}

# Test memory system components
test_memory_system() {
    echo -e "${BLUE}🧪 Testing memory system components...${NC}"
    
    # Test AgentMemoryManager
    echo -e "${YELLOW}   Testing AgentMemoryManager...${NC}"
    python3 -c "
import sys
import os
sys.path.append('containers/templates/agent-process')

try:
    from agent_memory_manager import AgentMemoryManager, MemoryType
    print('✅ AgentMemoryManager import successful')
except Exception as e:
    print(f'❌ AgentMemoryManager test failed: {e}')
    exit(1)
"

    # Test ClaudeClientWithMemory
    echo -e "${YELLOW}   Testing ClaudeClientWithMemory...${NC}"
    python3 -c "
import sys
import os
sys.path.append('containers/templates/agent-process')

try:
    from claude_client_with_memory import ClaudeClientWithMemory
    print('✅ ClaudeClientWithMemory import successful')
except Exception as e:
    print(f'❌ ClaudeClientWithMemory test failed: {e}')
    exit(1)
"

    # Test autonomous agent
    echo -e "${YELLOW}   Testing AutonomousAgentWithMemory...${NC}"
    python3 -c "
import sys
import os
sys.path.append('containers/templates/agent-process')

try:
    from autonomous_agent_with_memory import AutonomousAgentWithMemory
    print('✅ AutonomousAgentWithMemory import successful')
except Exception as e:
    print(f'❌ AutonomousAgentWithMemory test failed: {e}')
    exit(1)
"

    echo -e "${GREEN}✅ All memory system components tested successfully${NC}"
}

# Create sample data for testing
create_sample_data() {
    echo -e "${BLUE}📊 Creating sample data for testing...${NC}"
    
    python3 -c "
import asyncpg
import asyncio
import os
import uuid
from datetime import datetime

async def create_sample_data():
    try:
        conn = await asyncpg.connect(os.environ['DATABASE_URL'])
        
        # Create sample organization
        org_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO organizations (id, name, description)
            VALUES (\$1, 'Sample Development Team', 'Sample organization for testing memory-enabled agents')
            ON CONFLICT (name) DO NOTHING
        ''', org_id)
        
        # Get or create organization
        org = await conn.fetchrow('SELECT id FROM organizations WHERE name = \$1', 'Sample Development Team')
        org_id = org['id']
        
        # Create sample team
        team_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO teams (id, organization_id, name, description)
            VALUES (\$1, \$2, 'Frontend Development', 'Sample frontend development team')
            ON CONFLICT (organization_id, name) DO NOTHING
        ''', team_id, org_id)
        
        # Get or create team
        team = await conn.fetchrow('SELECT id FROM teams WHERE name = \$1 AND organization_id = \$2', 'Frontend Development', org_id)
        team_id = team['id']
        
        # Create sample agent
        agent_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO agents (id, team_id, name, role, type, status, config)
            VALUES (\$1, \$2, 'React Developer AI', 'Senior React Developer', 'developer', 'active', \$3)
            ON CONFLICT (team_id, name) DO NOTHING
        ''', agent_id, team_id, {
            'goal': 'Build responsive React applications with modern UI/UX',
            'backstory': 'Expert React developer with persistent memory and learning capabilities',
            'model': 'claude-3-5-sonnet-20241022',
            'temperature': 0.3,
            'memory_enabled': True
        })
        
        await conn.close()
        print('✅ Sample data created successfully')
        print(f'   Organization ID: {org_id}')
        print(f'   Team ID: {team_id}')
        
        # Get actual agent ID
        conn = await asyncpg.connect(os.environ['DATABASE_URL'])
        agent = await conn.fetchrow('SELECT id FROM agents WHERE name = \$1', 'React Developer AI')
        if agent:
            print(f'   Agent ID: {agent[\"id\"]}')
        await conn.close()
        
    except Exception as e:
        print(f'❌ Failed to create sample data: {e}')

asyncio.run(create_sample_data())
"
}

# Main deployment function
main() {
    echo -e "${BLUE}Starting FuzeAgent Memory System Deployment${NC}"
    echo ""
    
    # Run all deployment steps
    check_env_vars
    echo ""
    
    check_database
    echo ""
    
    install_dependencies
    echo ""
    
    run_migrations
    echo ""
    
    build_containers
    echo ""
    
    test_memory_system
    echo ""
    
    create_sample_data
    echo ""
    
    echo -e "${GREEN}🎉 FuzeAgent Memory System Deployment Complete!${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Start the orchestrator service:"
    echo "   cd services/orchestrator && uvicorn main:app --host 0.0.0.0 --port 8000"
    echo ""
    echo "2. Deploy a memory-enabled agent:"
    echo "   curl -X POST http://localhost:8000/agents/{agent_id}/deploy-memory \\"
    echo "        -H 'Content-Type: application/json' \\"
    echo "        -d '{\"template_id\": \"python_developer\"}'"
    echo ""
    echo "3. View system expertise dashboard:"
    echo "   curl http://localhost:8000/system/expertise-dashboard"
    echo ""
    echo "4. Check agent memory status:"
    echo "   curl http://localhost:8000/agents/{agent_id}/memory-status"
    echo ""
    echo -e "${GREEN}The persistent memory system is now ready for AI agents!${NC}"
}

# Run main function
main