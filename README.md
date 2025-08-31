# FuzeAgent - AI Team Orchestration Platform
## Version 0.0.1.0

FuzeAgent is a comprehensive AI team orchestration platform that creates and manages autonomous AI agents using Claude Code SDK and CrewAI. The system implements a distributed microservices architecture where multiple AI agents collaborate to complete complex software development tasks, coordinated by a digital CEO (IzzyAI).

## 🎉 What's New in Version 0.0.1.0

### ✨ Major Features
- **Full UI Implementation**: Complete React-based management interface now fully functional
- **Direct Database Integration**: UI now communicates directly with the Hierarchy API service
- **Separated Database Service**: Database management moved to dedicated microservice for better scalability
- **API-First Architecture**: All UI functionality now backed by comprehensive REST API endpoints

### 🔄 Architecture Changes
- **New Hierarchy API Service**: Dedicated FastAPI service handling all UI-database communication
- **Database Service Separation**: PostgreSQL management now runs as independent microservice
- **Direct API Integration**: UI bypasses orchestrator for immediate database operations
- **Streamlined Data Flow**: Simplified architecture for better performance and reliability

## 🏗️ Updated Architecture (v0.0.1.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Management UI (React)                        │ 
│                  + WebSocket + D3.js                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Direct API Communication
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Hierarchy API Service                         │
│                     (FastAPI + AsyncPG)                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Direct Database Access
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Database Service                              │
│                    (PostgreSQL + pgvector)                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                          │
│  ┌───────────────────┐  ┌─────────────────┐  ┌───────────────┐ │
│  │ Orchestrator API  │  │  Message Queue  │  │  Agent Mgmt   │ │
│  │   (FastAPI)       │  │   (RabbitMQ)    │  │   (CrewAI)    │ │
│  └───────────────────┘  └─────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                        Agent Containers                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  IzzyAI CEO │  │   CTO Agent │  │  CPO Agent  │  ...       │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │Frontend Dev1│  │Frontend Dev2│  │Backend Dev1 │  ...       │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└──────────────────────────────────────────────────────────────────┘
```

### Key Architectural Improvements
- **Direct UI-Database Communication**: Management UI now connects directly to Hierarchy API service
- **Separated Concerns**: Database operations isolated from agent orchestration
- **Better Performance**: Eliminated unnecessary proxy layers for UI operations
- **Independent Scaling**: Database and orchestration services can scale independently

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenSSL (for generating secure passwords)
- curl (for API calls)

### Setup

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd FuzeAgent
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Add your API key:**
   - Edit `.env` file
   - Replace `your-api-key-here` with your actual Anthropic API key

3. **Start the system:**
   ```bash
   docker-compose up -d
   ```

4. **Verify installation:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/agents
   ```

## 🎛️ Services

### Core Infrastructure
- **PostgreSQL** (port 5434): Primary database with pgvector for embeddings
- **RabbitMQ** (port 5672, management 15673): Message queue for agent communication  
- **Redis** (port 6380): Caching and session storage

### Application Services (New in v0.0.1.0)
- **Management UI** (port 3001): React-based dashboard - **Now Fully Functional** ✅
- **Hierarchy API** (port 8006): FastAPI service handling UI-database operations - **New** ✨
- **Database Service** (port 5434): Dedicated PostgreSQL management service - **New** ✨
- **Orchestrator** (port 8000): FastAPI service managing agents and tasks

## 🎯 Goals Management System

FuzeAgent includes a comprehensive Goals Management System for organizational planning and execution:

### Key Features
- **Strategic Goal Setting**: Create organizational objectives with deadlines and success criteria
- **AI-Powered Planning**: Automatic milestone and task generation from goals
- **Conversation Support**: AI-powered planning discussions and progress reviews
- **Cross-functional Coordination**: Tasks distributed across development, marketing, sales, and operations teams
- **Real-time Tracking**: Progress monitoring with risk assessment and automated alerts

### Example: Achieving $100K MRR
```bash
# Create organizational goal
curl -X POST http://localhost:8000/organizations/WCG/goals \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Reach $100K MRR",
    "description": "Achieve $100,000 monthly recurring revenue in 6 months",
    "target_value": 100000,
    "target_deadline": "2024-12-31",
    "priority_level": 10
  }'

# Generate execution plan with monthly milestones
curl -X POST http://localhost:8000/goals/{goal_id}/generate-execution-plan

# Create AI planning conversation
curl -X POST http://localhost:8000/goals/{goal_id}/conversations \
  -d '{"conversation_type": "planning", "conversation_title": "Strategic Planning"}'

# Track progress
curl -X POST http://localhost:8000/goals/{goal_id}/track-progress \
  -d '{"progress_percentage": 25.5, "current_value": 25500}'
```

## 🤖 Agent Types

### Executive Agents
- **IzzyAI (CEO)**: Strategic planning, resource allocation, team management
- **CTO Agent**: Technical architecture, developer coordination
- **CPO Agent**: Product planning, design oversight, quality assurance

### Developer Agents
- **Frontend Developers**: React, TypeScript, UI/UX implementation
- **Backend Developers**: FastAPI, database design, API development
- **Full-Stack Developers**: End-to-end feature implementation

### Specialist Agents
- **QA Engineers**: Test generation, automation, bug reporting
- **DevOps Engineers**: Infrastructure, deployment, monitoring
- **Designers**: UI mockups, accessibility, design systems

## 📡 API Endpoints

### Agent Management
```bash
# Create a new agent
POST /agents
{
  "name": "Frontend Dev 1",
  "role": "Senior React Developer", 
  "type": "developer",
  "config": {
    "goal": "Build responsive React components",
    "tools": ["code_generation", "code_review"],
    "model": "claude-sonnet-4-20250514"
  }
}

# List all agents
GET /agents

# Get agent status  
GET /agents/{agent_id}/status

# Assign task to agent
POST /agents/{agent_id}/tasks
{
  "title": "Implement user dashboard",
  "description": "Create a responsive dashboard component",
  "type": "implement_feature"
}
```

### Task Management
```bash
# List all tasks
GET /tasks

# Get specific task
GET /tasks/{task_id}
```

### Goals Management
```bash
# Create organizational goal
POST /organizations/{org_id}/goals
{
  "title": "Reach $100K MRR",
  "description": "Achieve revenue target in 6 months",
  "goal_type": "business",
  "target_value": 100000,
  "target_deadline": "2024-12-31",
  "priority_level": 10
}

# List organization goals
GET /organizations/{org_id}/goals?status=active&limit=25

# Get goal details
GET /goals/{goal_id}

# Update goal progress
PUT /goals/{goal_id}/progress
{
  "progress_percentage": 25.5,
  "current_value": 25000,
  "notes": "Good progress this month"
}

# Generate execution plan
POST /goals/{goal_id}/generate-execution-plan

# Create planning conversation
POST /goals/{goal_id}/conversations
{
  "conversation_type": "planning",
  "conversation_title": "Strategic Planning Session"
}

# Track progress with risk assessment
POST /goals/{goal_id}/track-progress
{
  "progress_percentage": 30.5,
  "confidence_score": 0.8
}

# Get deadline risk assessment
GET /goals/{goal_id}/deadline-risk

# Organization dashboard
GET /organizations/{org_id}/goals-dashboard
```

### System Health
```bash
# Health check
GET /health
```

## 🛠️ Development

### Project Structure (Updated v0.0.1.0)
```
FuzeAgent/
├── services/
│   ├── orchestrator/          # FastAPI orchestration service
│   ├── ui-react/              # React Management UI - NEW ✨
│   ├── hierarchy_API/         # Hierarchy API service - NEW ✨
│   └── database_service/      # Database management service - NEW ✨
├── containers/
│   ├── base-agent/           # Base agent container
│   ├── developer-agent/      # Developer-specific agent
│   └── executive-agent/      # Executive-specific agent (coming soon)
├── docs/                     # Documentation
├── docker-compose.yml        # Container orchestration
├── init_db.sql              # Database schema
└── setup.sh                 # Quick setup script
```

### New Service Details
- **ui-react/**: Complete React frontend with agent management, team hierarchies, goals tracking, and real-time monitoring
- **hierarchy_API/**: FastAPI service providing REST endpoints for UI operations with direct database access
- **database_service/**: Dedicated PostgreSQL service with optimized connection pooling and health monitoring

### Common Commands (Updated for v0.0.1.0)

```bash
# Access the Management UI (NEW!)
open http://localhost:3001

# View service logs
docker-compose logs -f ui-react          # React UI logs
docker-compose logs -f hierarchy_API     # Hierarchy API logs
docker-compose logs -f database_service  # Database service logs
docker-compose logs -f orchestrator      # Orchestrator logs

# Restart services
docker-compose restart
docker-compose restart ui-react          # Restart just the UI
docker-compose restart hierarchy_API     # Restart just the API

# Stop all services
docker-compose down

# Build and restart (recommended after code changes)
docker-compose build && docker-compose up -d

# Database access (via dedicated service)
docker-compose exec database_service psql -U postgres -d ai_context

# API Health Checks
curl http://localhost:8006/health         # Hierarchy API
curl http://localhost:8000/health         # Orchestrator
curl http://localhost:3001                # UI (should show React app)

# RabbitMQ management
open http://localhost:15673  # admin/[password from .env]
```

### Adding New Agent Types

1. Create new container directory: `containers/[agent-type]-agent/`
2. Extend `BaseAgent` class with specific functionality
3. Add agent type to orchestrator configuration
4. Update database schema if needed
5. Test agent creation and task execution

## 🔧 Configuration

### Environment Variables
See `.env.example` for all configuration options:

- `ANTHROPIC_API_KEY`: Your Claude API key (required)
- `POSTGRES_PASSWORD`: Database password (auto-generated)
- `RABBITMQ_PASSWORD`: Message queue password (auto-generated)
- `JWT_SECRET`: Security token secret (auto-generated)

### Claude Code Configuration
The system uses both global and project-specific Claude Code configurations:

- Global: `~/.claude_code_config`
- Project: `./.claude_code_config`

## 🏢 Agent Capabilities

### Developer Agent Tasks
- `implement_feature`: Create new functionality with tests and documentation
- `fix_bug`: Debug and resolve issues with regression tests
- `code_review`: Analyze code quality and provide recommendations
- `refactor_code`: Improve code structure and maintainability

### Executive Agent Tasks
- `strategic_planning`: High-level project planning and architecture decisions
- `resource_allocation`: Distribute tasks and manage team capacity
- `team_management`: Coordinate agent activities and resolve conflicts

### Goals-Driven Task Generation
- **Milestone Creation**: AI automatically generates time-bound milestones from organizational goals
- **Cross-Functional Tasks**: Goals spawn tasks across development, marketing, sales, and operations teams
- **Dynamic Assignment**: Tasks automatically assigned to appropriate agents based on skills and availability
- **Progress Coordination**: Real-time progress updates flow from tasks → milestones → goals
- **Risk Management**: Automated risk assessment and mitigation strategy generation

## 📊 Monitoring

### Health Checks (Updated for v0.0.1.0)
- **Management UI**: `http://localhost:3001` - **Now Available** ✅
- **Hierarchy API**: `http://localhost:8006/health` - **New** ✨
- **Database Service**: `docker-compose exec database_service pg_isready` - **Updated** ✨
- **Orchestrator**: `http://localhost:8000/health`
- **RabbitMQ**: `http://localhost:15673`

### Observability (Enhanced in v0.0.1.0)
- **Full UI Dashboard**: Real-time agent monitoring, task tracking, and system metrics ✅
- **Interactive Agent Management**: Create, configure, and monitor agents through web interface ✅
- **Knowledge Management**: Upload documents and manage agent knowledge bases through UI ✅
- **Team Hierarchies**: Visual organization charts and team management ✅
- **Goal Tracking**: Complete goals management with progress visualization ✅
- Structured logging with correlation IDs
- Real-time WebSocket updates
- Task completion metrics
- Agent utilization tracking

## 🔒 Security

### Best Practices
- Non-root users in all containers
- Environment variable-based secrets
- JWT-based authentication
- Network isolation between services
- Regular security updates

### API Security
- Rate limiting on critical endpoints
- Input validation for all requests
- Audit logging for administrative actions
- Secure default configurations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting (Updated for v0.0.1.0)

### Common Issues

**UI Not Loading**
- Verify React service is running: `docker-compose ps ui-react`
- Check UI logs: `docker-compose logs ui-react`
- Ensure port 3001 is available: `curl http://localhost:3001`

**API Endpoints Not Working**
- Verify Hierarchy API is running: `curl http://localhost:8006/health`
- Check API logs: `docker-compose logs hierarchy_API`
- Ensure database service is connected: `docker-compose ps database_service`

**Agent Creation Fails**
- Verify `ANTHROPIC_API_KEY` is set correctly
- Check database connectivity: `docker-compose ps database_service`
- Ensure RabbitMQ is running: `docker-compose ps rabbitmq`
- Try creating agent through UI at `http://localhost:3001/agents`

**Tasks Not Processing**
- Check agent container status: `docker-compose ps`
- View orchestrator logs: `docker-compose logs orchestrator`
- Verify message queue: http://localhost:15673

**Database Connection Issues**
- Restart database service: `docker-compose restart database_service`
- Check database logs: `docker-compose logs database_service`
- Verify connection string in `.env`
- Test connection: `docker-compose exec database_service pg_isready`

### Getting Help

- **Check the Management UI**: http://localhost:3001 for visual system status
- **API Health Checks**: 
  - UI: http://localhost:3001
  - Hierarchy API: http://localhost:8006/health  
  - Orchestrator: http://localhost:8000/health
- **Service Logs**: `docker-compose logs -f [service_name]`
- **Database Status**: Use UI or `curl http://localhost:8006/agents`
- **Consult Documentation**: `CLAUDE.md` for detailed guidance

---

## 🎯 Version 0.0.1.0 Summary

This major release transforms FuzeAgent from a backend-only system to a **fully functional web application**:

✅ **Complete React UI** - Beautiful, responsive management interface  
✅ **Direct Database Integration** - Fast, reliable data operations  
✅ **Microservice Architecture** - Scalable, maintainable service separation  
✅ **Real-time Monitoring** - Live system status and agent management  
✅ **Knowledge Management** - Document upload and URL integration  
✅ **Team Hierarchies** - Visual organization management  
✅ **Goal Tracking** - Comprehensive goal and milestone management  

**Ready to use at: http://localhost:3001** 🚀

---

**Built with ❤️ using Claude Code SDK and CrewAI**