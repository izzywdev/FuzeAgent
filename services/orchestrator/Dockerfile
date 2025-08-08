# Base dependencies stage
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies for autonomous execution
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    wget \
    openssh-client \
    gnupg \
    software-properties-common \
    build-essential \
    libffi-dev \
    libssl-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Dependencies stage  
FROM base as dependencies

# Copy requirements and install Python dependencies with caching
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Install Claude Code CLI
RUN curl -fsSL https://claude.ai/install.sh | bash

# Runtime stage
FROM base as runtime

# Copy installed packages from dependencies stage
COPY --from=dependencies /root/.local /root/.local

# Make sure scripts in .local are usable (Claude CLI is installed here)
ENV PATH=/root/.local/bin:$PATH

# Copy source code
COPY . .

# Copy entrypoint script and set permissions before switching user
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create non-root user and set ownership
RUN useradd -m -u 1000 orchestrator && \
    chown -R orchestrator:orchestrator /app
USER orchestrator

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Set environment variable for migrations
ENV RUN_MIGRATIONS=true

# Run the application
ENTRYPOINT ["/app/entrypoint.sh"]