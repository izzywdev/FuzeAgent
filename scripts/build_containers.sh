#!/bin/bash

# Build script for FuzeAgent development containers
# This script builds all the dev container templates with agent processes

set -e

echo "🔨 Building FuzeAgent development containers..."

# Navigate to containers directory
cd "$(dirname "$0")/../containers/templates"

# Build base development container
echo "📦 Building base development container..."
docker build -t fuzeagent/dev-base:latest dev-base/

echo "📦 Building Python development container..."
docker build -t fuzeagent/dev-python:latest dev-python/

echo "📦 Building TypeScript development container..."
docker build -t fuzeagent/dev-typescript:latest dev-typescript/

echo "📦 Building React development container..."
docker build -t fuzeagent/dev-react:latest dev-react/

echo "✅ All containers built successfully!"

# Show built images
echo "📋 Built images:"
docker images | grep fuzeagent/dev

echo ""
echo "🚀 Containers are ready for autonomous agent execution!"
echo "Each container includes:"
echo "  - Claude Code CLI (placeholder)"
echo "  - Autonomous agent process"
echo "  - Development tools and environment"
echo "  - Git and GitHub CLI integration"