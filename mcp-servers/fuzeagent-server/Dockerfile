FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY README.md .

# Create non-root user
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser
RUN chown -R mcpuser:mcpuser /app
USER mcpuser

# Expose port for SSE mode
EXPOSE 8001

# Default environment variables
ENV FUZEAGENT_API_URL=http://localhost:8000

# Default command (can be overridden)
CMD ["python", "server.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8001"]