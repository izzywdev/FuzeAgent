#!/bin/bash
# Build script for FuzeAgent development container templates

set -e

echo "🚀 Building FuzeAgent Dev Container Templates"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

build_container() {
    local template_name=$1
    local dockerfile_path=$2
    
    echo -e "${BLUE}Building ${template_name}...${NC}"
    
    if [ ! -f "$dockerfile_path/Dockerfile" ]; then
        echo -e "${RED}❌ Dockerfile not found at $dockerfile_path/Dockerfile${NC}"
        return 1
    fi
    
    docker build -t "fuzeagent/$template_name:latest" "$dockerfile_path"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Successfully built fuzeagent/$template_name:latest${NC}"
    else
        echo -e "${RED}❌ Failed to build fuzeagent/$template_name:latest${NC}"
        return 1
    fi
}

# Build base template first (others depend on it)
echo -e "${YELLOW}Building base development container...${NC}"
build_container "dev-base" "./dev-base"

# Build TypeScript template (React depends on it)
echo -e "${YELLOW}Building TypeScript development container...${NC}"
build_container "dev-typescript" "./dev-typescript"

# Build Python template
echo -e "${YELLOW}Building Python development container...${NC}"
build_container "dev-python" "./dev-python"

# Build React template
echo -e "${YELLOW}Building React development container...${NC}"
build_container "dev-react" "./dev-react"

echo -e "${GREEN}🎉 All development containers built successfully!${NC}"

# Show built images
echo -e "${BLUE}📋 Available FuzeAgent development containers:${NC}"
docker images | grep fuzeagent/dev- | sort

echo ""
echo -e "${YELLOW}💡 Usage examples:${NC}"
echo "  docker run -it --rm fuzeagent/dev-python:latest"
echo "  docker run -it --rm -v \$(pwd):/workspaces fuzeagent/dev-react:latest"
echo "  docker run -it --rm -p 8000:8000 fuzeagent/dev-typescript:latest"

echo ""
echo -e "${GREEN}✨ Ready for autonomous agent development!${NC}"