# Releasing the FuzeAgent Database as a Standalone Service

This document explains how to release and use the FuzeAgent database as a standalone service.

## Overview

The FuzeAgent database service is a standalone PostgreSQL database that contains all the necessary schema for the FuzeAgent AI team orchestration platform. It can be deployed independently and used by other services.

## Directory Structure

The database service is located in the `database_service` directory and contains:

- `Dockerfile` - Docker configuration for the database service
- `init-scripts/` - SQL initialization scripts
- `README.md` - Documentation for the database service
- Utility scripts for testing, initialization, and management

## Prerequisites

To deploy the database service, you need:

1. Docker installed on the target system
2. Access to a Docker registry (for publishing the image)
3. Basic knowledge of Docker and PostgreSQL

## Building and Publishing the Database Image

### 1. Build the Docker Image

```bash
cd database_service
docker build -t fuzeagent-db:latest .
```

### 2. Tag the Image for Distribution

```bash
# Tag for a specific registry (replace with your registry)
docker tag fuzeagent-db:latest your-registry.com/fuzeagent-db:latest
docker tag fuzeagent-db:latest your-registry.com/fuzeagent-db:v1.0.0
```

### 3. Push to Registry

```bash
# Push to your registry
docker push your-registry.com/fuzeagent-db:latest
docker push your-registry.com/fuzeagent-db:v1.0.0
```

## Deployment Options

### Option 1: Using Docker Run

```bash
docker run -d \
  --name fuzeagent-db \
  -p 5432:5432 \
  -e POSTGRES_DB=ai_context \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your-password \
  -v db_data:/var/lib/postgresql/data \
  your-registry.com/fuzeagent-db:latest
```

### Option 2: Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  database:
    image: your-registry.com/fuzeagent-db:latest
    container_name: fuzeagent-db
    environment:
      POSTGRES_DB: ai_context
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your-password
    ports:
      - "5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d ai_context"]
      interval: 30s
      timeout: 30s
      retries: 3

volumes:
  db_data:
```

Then run:

```bash
docker-compose up -d
```

### Option 3: Kubernetes Deployment

Create a `deployment.yaml` file:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fuzeagent-db
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fuzeagent-db
  template:
    metadata:
      labels:
        app: fuzeagent-db
    spec:
      containers:
      - name: database
        image: your-registry.com/fuzeagent-db:latest
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: "ai_context"
        - name: POSTGRES_USER
          value: "postgres"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
        volumeMounts:
        - name: db-data
          mountPath: /var/lib/postgresql/data
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
            - -d
            - ai_context
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
            - -d
            - ai_context
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: db-data
        persistentVolumeClaim:
          claimName: db-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: fuzeagent-db
spec:
  selector:
    app: fuzeagent-db
  ports:
    - protocol: TCP
      port: 5432
      targetPort: 5432
  type: ClusterIP
---
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  password: eW91ci1wYXNzd29yZA==  # base64 encoded "your-password"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: db-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

Apply the deployment:

```bash
kubectl apply -f deployment.yaml
```

## Connecting to the Database

Once deployed, you can connect to the database using:

### Connection Parameters

- Host: localhost (or service name in Docker/Kubernetes)
- Port: 5432
- Database: ai_context
- Username: postgres
- Password: your-password (as set in environment variables)

### Using psql

```bash
psql -h localhost -p 5432 -U postgres -d ai_context
```

### Using Python (asyncpg)

```python
import asyncpg
import asyncio

async def connect_to_db():
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="your-password",
        database="ai_context"
    )
    return conn

# Example usage
async def main():
    conn = await connect_to_db()
    # Your database operations here
    await conn.close()

asyncio.run(main())
```

## Database Schema

The database schema includes:

### Core Tables

1. **organizations** - Store organization information
2. **teams** - Store team information within organizations
3. **agents** - Store AI agent information
4. **tasks** - Store tasks assigned to agents
5. **chat_sessions** - Store chat session information
6. **agent_conversations** - Store individual messages in chat sessions

### Model Configuration Tables

1. **organization_provider_credentials** - Store encrypted API credentials for model providers
2. **agent_model_configurations** - Store model configuration for each agent
3. **model_usage_logs** - Track model usage for billing and analytics
4. **model_usage_daily_aggregates** - Daily aggregated usage statistics

### Views

1. **organization_model_usage_summary** - Summary of model usage by organization
2. **agent_model_usage_summary** - Summary of model usage by agent

## Maintenance

### Backups

Create a backup:

```bash
docker exec fuzeagent-db pg_dump -U postgres ai_context > backup.sql
```

Restore from a backup:

```bash
docker exec -i fuzeagent-db psql -U postgres ai_context < backup.sql
```

### Updates

To update the database schema:

1. Create new SQL migration files in `init-scripts` with the next number in sequence
2. Rebuild and redeploy the Docker image
3. Apply the migrations to the running database

## Monitoring

The database service includes health checks that can be monitored:

### Docker Health Check

```bash
docker inspect fuzeagent-db | grep Health
```

### Kubernetes Liveness and Readiness Probes

The Kubernetes deployment includes both liveness and readiness probes for automatic health monitoring.

## Troubleshooting

### Common Issues

1. **Connection refused**: Ensure the container is running and the port is correctly mapped
2. **Authentication failed**: Check the username and password
3. **Database does not exist**: Verify the `POSTGRES_DB` environment variable

### Logs

View container logs:

```bash
docker logs fuzeagent-db
```

### Direct Access

Connect to the container shell:

```bash
docker exec -it fuzeagent-db sh
```

## Conclusion

The FuzeAgent database service is designed to be easily deployable as a standalone service. It includes all the necessary schema and initialization scripts to get started quickly, along with utility scripts for testing, initialization, and migration.

For detailed usage instructions, refer to the [Database Service README](./database_service/README.md).