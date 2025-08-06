#!/bin/bash

# Wait for services to be healthy
set -e

echo "⏳ Waiting for services to start..."

# Function to wait for HTTP service
wait_for_http() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo "✅ $name is ready"
            return 0
        fi
        echo "⏳ Waiting for $name... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ $name failed to start"
    return 1
}

# Wait for database
echo "⏳ Waiting for database..."
sleep 5

# Wait for core services
wait_for_http "http://localhost:8000/health" "Orchestrator"
wait_for_http "http://localhost:8006/organizations" "Hierarchy API"
wait_for_http "http://localhost:3030" "UI"

echo "🎉 All services are ready!"