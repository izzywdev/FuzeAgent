# FuzeAgent - AI Team Orchestration Platform

FuzeAgent is a comprehensive AI team orchestration platform that creates and manages autonomous AI agents using Claude Code SDK and CrewAI. The system implements a distributed microservices architecture where multiple AI agents collaborate to complete complex software development tasks, coordinated by a digital CEO (IzzyAI).

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Management UI                            │
│                    (React + WebSocket + D3.js)                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                 Orchestration Service (FastAPI)                  │
│                        + CrewAI Core                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                      Message Queue (RabbitMQ)                    │
└─────────────────────────┬───────────────────────────────────────┘
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
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                     Shared Services                              │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐       │
│  │Context Store │  │  MCP Servers │  │  Code Storage  │       │
│  │  (Postgres)  │  │   (Node.js)  │  │   (GitLab)    │       │
│  └──────────────┘  └──────────────┘  └────────────────┘       │
└──────────────────────────────────────────────────────────────────┘
```

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
- **PostgreSQL** (port 5432): Primary database with pgvector for embeddings
- **RabbitMQ** (port 5672, management 15672): Message queue for agent communication
- **Redis** (port 6379): Caching and session storage

### Application Services
- **Orchestrator** (port 8000): FastAPI service managing agents and tasks
- **Management UI** (port 3000): React-based dashboard (coming soon)

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

### System Health
```bash
# Health check
GET /health
```

## 🛠️ Development

### Project Structure
```
FuzeAgent/
├── services/
│   └── orchestrator/          # FastAPI orchestration service
├── containers/
│   ├── base-agent/           # Base agent container
│   ├── developer-agent/      # Developer-specific agent
│   └── executive-agent/      # Executive-specific agent (coming soon)
├── docs/                     # Documentation
├── docker-compose.yml        # Container orchestration
├── init_db.sql              # Database schema
└── setup.sh                 # Quick setup script
```

### Common Commands

```bash
# View logs
docker-compose logs -f [service_name]

# Restart services
docker-compose restart

# Stop all services
docker-compose down

# Build and restart
docker-compose build && docker-compose up -d

# Database access
docker-compose exec postgres psql -U postgres -d ai_context

# RabbitMQ management
open http://localhost:15672  # admin/[password from .env]
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

## 📊 Monitoring

### Health Checks
- **Orchestrator**: `http://localhost:8000/health`
- **Database**: `docker-compose exec postgres pg_isready`
- **RabbitMQ**: `http://localhost:15672`

### Observability
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

## 🆘 Troubleshooting

### Common Issues

**Agent Creation Fails**
- Verify `ANTHROPIC_API_KEY` is set correctly
- Check database connectivity: `docker-compose ps postgres`
- Ensure RabbitMQ is running: `docker-compose ps rabbitmq`

**Tasks Not Processing**
- Check agent container status: `docker-compose ps`
- View orchestrator logs: `docker-compose logs orchestrator`
- Verify message queue: http://localhost:15672

**Database Connection Issues**
- Restart PostgreSQL: `docker-compose restart postgres`
- Check database logs: `docker-compose logs postgres`
- Verify connection string in `.env`

### Getting Help

- Check the logs: `docker-compose logs -f`
- Verify service health: `curl http://localhost:8000/health`
- Review agent status: `curl http://localhost:8000/agents`
- Consult `CLAUDE.md` for detailed guidance

---

**Built with ❤️ using Claude Code SDK and CrewAI**