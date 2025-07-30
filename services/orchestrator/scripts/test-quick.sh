#!/bin/bash

# Quick test runner for development
# Runs tests without Docker setup for faster feedback

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default test type
TEST_TYPE="unit"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        unit|integration|api|rag|a2a|mcp|all)
            TEST_TYPE="$1"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [TEST_TYPE]"
            echo ""
            echo "TEST_TYPE:"
            echo "  unit         Run unit tests only (default, fastest)"
            echo "  integration  Run integration tests (requires services)"
            echo "  api          Run API tests (requires services)"
            echo "  rag          Run RAG tests (requires services)"
            echo "  a2a          Run A2A protocol tests (requires services)"
            echo "  mcp          Run MCP server tests"
            echo "  all          Run all tests (requires services)"
            echo ""
            echo "Examples:"
            echo "  $0           # Run unit tests (fast)"
            echo "  $0 unit      # Run unit tests"
            echo "  $0 api       # Run API tests"
            exit 0
            ;;
        *)
            print_error "Unknown test type: $1"
            echo "Use -h for help"
            exit 1
            ;;
    esac
done

print_status "Running quick $TEST_TYPE tests..."

# Check if required dependencies are installed
if ! command -v python &> /dev/null; then
    print_error "Python is not installed"
    exit 1
fi

if ! python -c "import pytest" 2>/dev/null; then
    print_status "Installing pytest..."
    pip install pytest pytest-asyncio pytest-cov faker
fi

# Set environment variables for testing
export TESTING=1
export ANTHROPIC_API_KEY="test-api-key"

# For unit tests, we don't need real database connections
if [ "$TEST_TYPE" = "unit" ]; then
    export DATABASE_URL="postgresql://test:test@localhost:5432/test"
    export REDIS_URL="redis://localhost:6379"
    
    print_status "Running unit tests (no external services required)..."
    python -m pytest tests/ -m "unit" -v --tb=short
    
elif [ "$TEST_TYPE" = "mcp" ]; then
    export DATABASE_URL="postgresql://test:test@localhost:5432/test"
    
    print_status "Running MCP tests..."
    python -m pytest tests/test_mcp_server.py -v --tb=short
    
else
    # Integration tests require actual services
    print_status "Checking for required services..."
    
    # Check if test database is available
    if ! nc -z localhost 5434 2>/dev/null; then
        print_error "Test database not available on port 5434"
        print_error "Run 'docker-compose -f test_docker-compose.yml up -d' first"
        exit 1
    fi
    
    # Check if test redis is available
    if ! nc -z localhost 6380 2>/dev/null; then
        print_error "Test Redis not available on port 6380"
        print_error "Run 'docker-compose -f test_docker-compose.yml up -d' first"
        exit 1
    fi
    
    export DATABASE_URL="postgresql://postgres:password@localhost:5434/ai_context_test"
    export REDIS_URL="redis://localhost:6380"
    
    # Run migrations
    print_status "Running database migrations..."
    python -c "
import asyncio
from migration_manager import MigrationManager

async def migrate():
    manager = MigrationManager('$DATABASE_URL')
    result = await manager.migrate_up()
    print(f'Applied {result[\"applied_count\"]} migrations')
    await manager.close()

asyncio.run(migrate())
" || {
        print_error "Database migration failed"
        exit 1
    }
    
    case $TEST_TYPE in
        integration)
            python -m pytest tests/ -m "integration" -v --tb=short
            ;;
        api)
            python -m pytest tests/ -m "api" -v --tb=short
            ;;
        rag)
            python -m pytest tests/ -m "rag" -v --tb=short
            ;;
        a2a)
            python -m pytest tests/ -m "a2a" -v --tb=short
            ;;
        all)
            python -m pytest tests/ -v --tb=short
            ;;
    esac
fi

if [ $? -eq 0 ]; then
    print_success "All $TEST_TYPE tests passed!"
else
    print_error "Some tests failed"
    exit 1
fi