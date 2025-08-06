#!/bin/bash

# Production build script with optimizations
set -e

echo "🏭 Starting optimized production build..."

# Enable Docker BuildKit for better caching and multi-platform builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Clean up previous builds
echo "🧹 Cleaning up previous builds..."
docker system prune -f

# Build all services with optimizations
echo "📦 Building production services..."
docker-compose build --parallel --no-cache

# Optional: Tag images for registry
if [ "$1" = "--tag" ]; then
    echo "🏷️ Tagging images for registry..."
    docker tag fuzeagent-ui:latest your-registry/fuzeagent-ui:latest
    docker tag fuzeagent-orchestrator:latest your-registry/fuzeagent-orchestrator:latest
    docker tag fuzeagent-hierarchy-api:latest your-registry/fuzeagent-hierarchy-api:latest
fi

echo "✅ Production build complete!"