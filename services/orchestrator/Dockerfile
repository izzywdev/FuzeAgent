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

# Note: Claude Code CLI intentionally not installed at build time (install.sh hangs CI).
# Agents that need it mount it or install via entrypoint.

# Runtime stage
FROM base as runtime

# Copy installed packages from dependencies stage
COPY --from=dependencies /root/.local /root/.local

# Make sure scripts in .local are usable (Claude CLI is installed here)
ENV PATH=/root/.local/bin:$PATH

# Copy source code
COPY . .

# Copy entrypoint script and set permissions
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Run as root to avoid permission issues with installed packages
# Note: In production, consider using a non-root user with proper permissions
USER root

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Set environment variable for migrations
ENV RUN_MIGRATIONS=true

# Run the application
ENTRYPOINT ["/app/entrypoint.sh"]