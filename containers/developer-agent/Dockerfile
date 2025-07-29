FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    gcc \
    g++ \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN curl -fsSL https://claude.ai/install.sh | bash

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy base agent code
COPY ../base-agent/context_client.py ./
COPY ../base-agent/agent.py ./base_agent.py

# Copy developer-specific code
COPY agent.py .
COPY tools/ ./tools/

# Create non-root user
RUN useradd -m -u 1000 developer && \
    chown -R developer:developer /app
USER developer

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run developer agent
CMD ["python", "agent.py"]