#!/bin/bash
# optimized-build.sh - Smart rebuild script for FuzeAgent

set -e

echo "🔧 FuzeAgent Optimized Container Build"

# Check if docker buildx is available
if docker buildx version >/dev/null 2>&1; then
    echo "✅ Using Docker BuildKit for optimized builds"
    export DOCKER_BUILDKIT=1
fi

# Clean up old containers and images
echo "🧹 Cleaning up old containers..."
docker-compose down --remove-orphans
docker system prune -f --volumes

# Build with optimized settings
echo "🏗️ Building containers with cache optimization..."
DOCKER_BUILDKIT=1 docker-compose build \
    --parallel \
    --pull \
    --progress=plain \
    --build-arg BUILDKIT_INLINE_CACHE=1

# Verify builds completed successfully
echo "🔍 Verifying container builds..."
docker-compose config --quiet

# Start services with health checks
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Health check for core services
echo "🔍 Health checking services..."
services=("postgres:5434" "rabbitmq:15673" "redis:6380")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if nc -z localhost "$port" 2>/dev/null; then
        echo "✅ $name is ready on port $port"
    else
        echo "❌ $name is not responding on port $port"
    fi
done

# Display build summary
echo "📊 Build Summary:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | head -10
echo ""
docker system df

# Show container status
echo "📋 Container Status:"
docker-compose ps

echo "✅ Build completed successfully!"
echo "🌐 Services available:"
echo "   - Orchestrator API: http://localhost:8000"
echo "   - Hierarchy API: http://localhost:8006" 
echo "   - Management UI: http://localhost:3031"
echo "   - RabbitMQ Management: http://localhost:15673"