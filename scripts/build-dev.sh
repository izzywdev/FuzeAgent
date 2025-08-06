#!/bin/bash

# Development build script with optimizations
set -e

echo "🚀 Starting optimized development build..."

# Enable Docker BuildKit for better caching
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build with development overrides and caching
echo "📦 Building services with development optimizations..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --parallel

# Start services
echo "🏃 Starting development services..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
./scripts/wait-for-services.sh

echo "✅ Development environment ready!"
echo "📍 UI: http://localhost:3030"
echo "📍 API: http://localhost:8006"
echo "📍 Orchestrator: http://localhost:8000"