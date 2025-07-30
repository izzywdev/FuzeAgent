#!/bin/bash

# FuzeAgent Test Runner Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
TEST_TYPE="all"
VERBOSE=false
COVERAGE=true
CLEANUP=true
PARALLEL=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -t, --type TYPE     Test type to run (unit, integration, api, rag, a2a, mcp, all)"
            echo "  -v, --verbose       Enable verbose output"
            echo "  --no-coverage       Disable coverage reporting"
            echo "  --no-cleanup        Don't cleanup containers after tests"
            echo "  -p, --parallel      Run tests in parallel"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                          # Run all tests"
            echo "  $0 -t unit                  # Run only unit tests"
            echo "  $0 -t integration -v        # Run integration tests with verbose output"
            echo "  $0 --no-coverage --no-cleanup # Run without coverage and cleanup"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_status "Starting FuzeAgent test suite..."
print_status "Test type: $TEST_TYPE"
print_status "Verbose: $VERBOSE"
print_status "Coverage: $COVERAGE"
print_status "Cleanup: $CLEANUP"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install it and try again."
    exit 1
fi

# Function to cleanup containers
cleanup_containers() {
    if [ "$CLEANUP" = true ]; then
        print_status "Cleaning up test containers..."
        docker-compose -f test_docker-compose.yml down -v --remove-orphans
        print_success "Cleanup completed"
    else
        print_warning "Skipping cleanup (--no-cleanup flag used)"
    fi
}

# Trap to ensure cleanup on exit
trap cleanup_containers EXIT

# Start test infrastructure
print_status "Starting test infrastructure..."
docker-compose -f test_docker-compose.yml up -d fuzeagent-test-db fuzeagent-test-redis

# Wait for services to be healthy
print_status "Waiting for test services to be ready..."
for service in fuzeagent-test-db fuzeagent-test-redis; do
    print_status "Waiting for $service..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker-compose -f test_docker-compose.yml ps $service | grep -q "healthy"; then
            print_success "$service is ready"
            break
        fi
        sleep 2
        ((timeout-=2))
    done
    
    if [ $timeout -le 0 ]; then
        print_error "$service failed to become healthy within 60 seconds"
        docker-compose -f test_docker-compose.yml logs $service
        exit 1
    fi
done

# Install test dependencies if not already installed
print_status "Installing test dependencies..."
pip install -q pytest pytest-asyncio pytest-cov faker httpx

# Set test environment variables
export TESTING=1
export DATABASE_URL="postgresql://postgres:password@localhost:5434/ai_context_test"
export REDIS_URL="redis://localhost:6380"
export ANTHROPIC_API_KEY="test-api-key"

# Build pytest command
PYTEST_CMD="python -m pytest"

# Add test type filter
case $TEST_TYPE in
    unit)
        PYTEST_CMD="$PYTEST_CMD -m unit"
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD -m integration"
        ;;
    api)
        PYTEST_CMD="$PYTEST_CMD -m api"
        ;;
    rag)
        PYTEST_CMD="$PYTEST_CMD -m rag"
        ;;
    a2a)
        PYTEST_CMD="$PYTEST_CMD -m a2a"
        ;;
    mcp)
        PYTEST_CMD="$PYTEST_CMD -m mcp"
        ;;
    database)
        PYTEST_CMD="$PYTEST_CMD -m database"
        ;;
    slow)
        PYTEST_CMD="$PYTEST_CMD -m slow"
        ;;
    all)
        # Run all tests
        ;;
    *)
        print_error "Invalid test type: $TEST_TYPE"
        print_error "Valid types: unit, integration, api, rag, a2a, mcp, database, slow, all"
        exit 1
        ;;
esac

# Add verbose flag
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add coverage
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=. --cov-report=html --cov-report=term-missing"
fi

# Add parallel execution
if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

# Run database migrations
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

print_success "Database migrations completed"

# Run tests
print_status "Running tests..."
print_status "Command: $PYTEST_CMD"

if eval $PYTEST_CMD; then
    print_success "All tests passed!"
    
    # Show coverage report location if coverage was enabled
    if [ "$COVERAGE" = true ]; then
        print_status "Coverage report generated at: htmlcov/index.html"
    fi
    
    exit 0
else
    print_error "Some tests failed"
    exit 1
fi