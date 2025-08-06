#!/bin/bash
# Wrapper script to run FuzeAgent MCP server with virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the MCP server directory
cd "$SCRIPT_DIR"

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    # Activate existing virtual environment
    source venv/bin/activate
fi

# Run the MCP server with all passed arguments
python server.py "$@"