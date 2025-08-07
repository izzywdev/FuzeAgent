#!/bin/bash
# health-check.sh - Comprehensive health check for FuzeAgent services

set -e

echo "🏥 FuzeAgent Health Check"
echo "========================"

# Function to check HTTP endpoint
check_http() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_code"; then
        echo "✅ $name is healthy ($url)"
        return 0
    else
        echo "❌ $name is unhealthy ($url)"
        return 1
    fi
}

# Function to check TCP port
check_port() {
    local name=$1
    local host=$2
    local port=$3
    
    if nc -z "$host" "$port" 2>/dev/null; then
        echo "✅ $name is listening on $host:$port"
        return 0
    else
        echo "❌ $name is not responding on $host:$port"
        return 1
    fi
}

# Function to check Docker container status
check_container() {
    local name=$1
    local container=$2
    
    if docker-compose ps "$container" | grep -q "Up"; then
        echo "✅ $name container is running"
        return 0
    else
        echo "❌ $name container is not running"
        docker-compose logs --tail=10 "$container"
        return 1
    fi
}

echo "🐳 Container Status Check"
echo "-------------------------"
check_container "PostgreSQL" "postgres"
check_container "RabbitMQ" "rabbitmq" 
check_container "Redis" "redis"
check_container "Orchestrator" "orchestrator"
check_container "Hierarchy API" "hierarchy-api"
check_container "UI" "ui"

echo ""
echo "🌐 Port Connectivity Check"
echo "---------------------------"
check_port "PostgreSQL" "localhost" "5434"
check_port "RabbitMQ AMQP" "localhost" "5673"
check_port "RabbitMQ Management" "localhost" "15673"
check_port "Redis" "localhost" "6380"
check_port "Orchestrator API" "localhost" "8000"
check_port "Hierarchy API" "localhost" "8006"
check_port "Management UI" "localhost" "3031"

echo ""
echo "🔗 HTTP Endpoint Check"
echo "-----------------------"
check_http "Orchestrator Health" "http://localhost:8000/health"
check_http "Orchestrator Docs" "http://localhost:8000/docs"
check_http "Hierarchy API Health" "http://localhost:8006/health" || echo "⚠️  Hierarchy API health endpoint not available"
check_http "Management UI" "http://localhost:3031"
check_http "RabbitMQ Management" "http://localhost:15673" "401"

echo ""
echo "📊 Resource Usage"
echo "------------------"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

echo ""
echo "💾 Storage Usage"
echo "----------------"
docker system df

echo ""
echo "📋 Service Logs (Last 5 lines each)"
echo "------------------------------------"
for service in postgres rabbitmq redis orchestrator hierarchy-api ui; do
    echo "--- $service ---"
    docker-compose logs --tail=5 "$service" 2>/dev/null || echo "Service not found: $service"
    echo ""
done

echo "🏁 Health check completed!"

# Return appropriate exit code
if docker-compose ps | grep -q "Exit"; then
    echo "❌ Some services have exited"
    exit 1
else
    echo "✅ All services appear to be running"
    exit 0
fi