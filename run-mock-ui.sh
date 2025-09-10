#!/bin/bash

# FuzeAgent Mock Server + UI Runner Script
# This script runs the mock server in Docker and the UI locally

echo "🚀 Starting FuzeAgent Mock Server + UI..."

# Start the mock server in Docker
echo "📦 Starting Mock Server in Docker..."
docker-compose -f docker-compose.mock-ui.yml up -d

# Wait for mock server to be ready
echo "⏳ Waiting for Mock Server to be ready..."
until curl -f http://localhost:8001/health > /dev/null 2>&1; do
    echo "   Waiting for mock server..."
    sleep 2
done

echo "✅ Mock Server is ready at http://localhost:8001"

# Check if UI dependencies are installed
if [ ! -d "services/ui-react/node_modules" ]; then
    echo "📦 Installing UI dependencies..."
    cd services/ui-react
    npm install --legacy-peer-deps
    cd ../..
fi

# Set environment variable for UI
export REACT_APP_API_URL=http://localhost:8001

echo "🎨 Starting UI in development mode..."
echo "   UI will be available at http://localhost:3000"
echo "   Mock Server API docs at http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop both services"

# Start the UI
cd services/ui-react
npm start
