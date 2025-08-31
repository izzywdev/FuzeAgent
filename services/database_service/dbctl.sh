#!/bin/bash

# FuzeAgent Database Service Management Script

set -e

# Default values
DOCKER_IMAGE_NAME="fuzeagent-db"
DOCKER_CONTAINER_NAME="fuzeagent-db"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="ai_context"
DB_USER="postgres"
DB_PASSWORD="password"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[-]${NC} $1"
}

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
}

# Function to check if Docker daemon is running
check_docker_daemon() {
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
}

# Function to build the database image
build_image() {
    print_status "Building database Docker image..."
    docker build -t "$DOCKER_IMAGE_NAME" ./database_service
    print_success "Database image built successfully!"
}

# Function to run the database container
run_container() {
    print_status "Starting database container..."
    
    # Check if container is already running
    if docker ps -q -f name="$DOCKER_CONTAINER_NAME" | grep -q .; then
        print_warning "Database container is already running."
        return
    fi
    
    # Check if container exists but is stopped
    if docker ps -aq -f status=exited -f name="$DOCKER_CONTAINER_NAME" | grep -q .; then
        print_status "Starting existing container..."
        docker start "$DOCKER_CONTAINER_NAME"
    else
        # Run new container
        docker run -d \
            --name "$DOCKER_CONTAINER_NAME" \
            -p "$DB_PORT":"$DB_PORT" \
            -e POSTGRES_DB="$DB_NAME" \
            -e POSTGRES_USER="$DB_USER" \
            -e POSTGRES_PASSWORD="$DB_PASSWORD" \
            -v db_data:/var/lib/postgresql/data \
            "$DOCKER_IMAGE_NAME"
    fi
    
    print_success "Database container started!"
    print_status "Container name: $DOCKER_CONTAINER_NAME"
    print_status "Database URL: postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
}

# Function to stop the database container
stop_container() {
    print_status "Stopping database container..."
    
    if docker ps -q -f name="$DOCKER_CONTAINER_NAME" | grep -q .; then
        docker stop "$DOCKER_CONTAINER_NAME"
        print_success "Database container stopped!"
    else
        print_warning "Database container is not running."
    fi
}

# Function to remove the database container
remove_container() {
    print_status "Removing database container..."
    
    if docker ps -aq -f name="$DOCKER_CONTAINER_NAME" | grep -q .; then
        docker rm "$DOCKER_CONTAINER_NAME"
        print_success "Database container removed!"
    else
        print_warning "Database container does not exist."
    fi
}

# Function to view database logs
view_logs() {
    print_status "Viewing database logs (Ctrl+C to exit)..."
    docker logs -f "$DOCKER_CONTAINER_NAME"
}

# Function to connect to database with psql
connect_psql() {
    print_status "Connecting to database with psql..."
    
    if docker ps -q -f name="$DOCKER_CONTAINER_NAME" | grep -q .; then
        docker exec -it "$DOCKER_CONTAINER_NAME" psql -U "$DB_USER" "$DB_NAME"
    else
        print_error "Database container is not running."
        exit 1
    fi
}

# Function to check container status
check_status() {
    print_status "Checking database container status..."
    
    if docker ps -q -f name="$DOCKER_CONTAINER_NAME" | grep -q .; then
        print_success "Database container is running."
        docker ps -f name="$DOCKER_CONTAINER_NAME"
    elif docker ps -aq -f status=exited -f name="$DOCKER_CONTAINER_NAME" | grep -q .; then
        print_warning "Database container exists but is stopped."
        docker ps -a -f name="$DOCKER_CONTAINER_NAME"
    else
        print_warning "Database container does not exist."
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build     - Build the database Docker image"
    echo "  run       - Run the database container"
    echo "  stop      - Stop the database container"
    echo "  remove    - Remove the database container"
    echo "  logs      - View database logs"
    echo "  psql      - Connect to database with psql"
    echo "  status    - Check container status"
    echo "  restart   - Restart the database container"
    echo "  clean     - Stop and remove the database container"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 run"
    echo "  $0 status"
}

# Main function
main() {
    # Check if command is provided
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    # Check Docker installation
    check_docker
    check_docker_daemon
    
    # Execute command
    case "$1" in
        build)
            build_image
            ;;
        run)
            run_container
            ;;
        stop)
            stop_container
            ;;
        remove)
            remove_container
            ;;
        logs)
            view_logs
            ;;
        psql)
            connect_psql
            ;;
        status)
            check_status
            ;;
        restart)
            stop_container
            run_container
            ;;
        clean)
            stop_container
            remove_container
            ;;
        *)
            print_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"