#!/bin/bash
# setup.sh - Quick setup script for AI Team

echo "🚀 Setting up AI Team Infrastructure..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Check if .env exists, if not create from example
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    
    # Generate .env file with secure passwords
    cat > .env << EOF
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
RABBITMQ_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
ANTHROPIC_API_KEY=your-api-key-here
JWT_SECRET=$(openssl rand -base64 32)
NODE_ENV=development
DEBUG=true
CLAUDE_CODE_ENABLE_TELEMETRY=1
CLAUDE_CODE_WORKSPACE_ID=fuzeagent
CLAUDE_CODE_PROJECT_NAME=FuzeAgent
EOF
    
    echo "⚠️  Please add your ANTHROPIC_API_KEY to .env file before continuing"
    echo "   Edit .env and replace 'your-api-key-here' with your actual API key"
    read -p "Press Enter when you've added your API key..."
fi

# Build base images
echo "🔨 Building base images..."
docker-compose build --no-cache

# Create network
echo "🌐 Creating Docker network..."
docker network create ai-team-network 2>/dev/null || echo "Network already exists"

# Initialize database
echo "💾 Initializing database..."
docker-compose up -d postgres
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 10

# Check if database is ready
until docker-compose exec postgres pg_isready -U postgres; do
    echo "⏳ Waiting for database..."
    sleep 2
done

echo "✅ Database is ready"

# Start core services
echo "🎯 Starting core services..."
docker-compose up -d rabbitmq redis

echo "⏳ Waiting for services to be ready..."
sleep 15

# Start orchestrator
echo "🤖 Starting orchestrator..."
docker-compose up -d orchestrator

echo "⏳ Waiting for orchestrator to be ready..."
sleep 10

# Check orchestrator health
echo "🔍 Checking orchestrator health..."
until curl -f http://localhost:8000/health >/dev/null 2>&1; do
    echo "⏳ Waiting for orchestrator..."
    sleep 3
done

echo "✅ Orchestrator is ready"

# Create initial IzzyAI agent
echo "👔 Creating IzzyAI CEO..."
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "IzzyAI",
    "role": "Digital CEO",
    "type": "executive",
    "config": {
      "goal": "Lead the AI team to build amazing products",
      "backstory": "Visionary AI leader with deep understanding of technology and business",
      "tools": ["strategic_planning", "resource_allocation", "team_management"],
      "model": "claude-sonnet-4-20250514",
      "temperature": 0.7
    }
  }' || echo "⚠️  Agent creation failed - orchestrator may need more time"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📊 Services Status:"
echo "   • Database (PostgreSQL): http://localhost:5432"
echo "   • Message Queue (RabbitMQ): http://localhost:15672 (admin/[password from .env])"
echo "   • Cache (Redis): localhost:6379"
echo "   • Orchestrator API: http://localhost:8000"
echo "   • Health Check: http://localhost:8000/health"
echo ""
echo "🔍 Next steps:"
echo "   1. Check service logs: docker-compose logs -f"
echo "   2. View agents: curl http://localhost:8000/agents"
echo "   3. Create more agents via API"
echo "   4. Assign tasks and watch the magic happen!"
echo ""
echo "🛠️  Useful commands:"
echo "   • View logs: docker-compose logs -f [service]"
echo "   • Stop services: docker-compose down"
echo "   • Restart services: docker-compose restart"
echo "   • View agent status: curl http://localhost:8000/agents"