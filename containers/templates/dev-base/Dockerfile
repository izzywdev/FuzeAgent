FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# Install essential development tools
RUN apt-get update && apt-get install -y \
    # Development essentials
    build-essential \
    git \
    curl \
    wget \
    unzip \
    # Network tools
    net-tools \
    iputils-ping \
    # Text editors
    vim \
    nano \
    # Process management
    htop \
    procps \
    # Archive tools  
    zip \
    unzip \
    tar \
    # SSL/TLS support
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install Python3 and pip for agent process
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI (placeholder - will be replaced with actual installation)
# Note: The actual Claude Code CLI installation will depend on the official release
# For now, we'll prepare the environment
RUN mkdir -p /usr/local/bin && \
    echo '#!/bin/bash' > /usr/local/bin/claude && \
    echo 'echo "Claude Code CLI placeholder - install actual CLI when available"' >> /usr/local/bin/claude && \
    chmod +x /usr/local/bin/claude

# Install Docker CLI (for agent containers that need Docker)
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Set up workspace directory
RUN mkdir -p /workspaces && chmod 755 /workspaces

# Create agent user with sudo privileges
RUN useradd -l -u 1000 -G sudo -md /home/agent -s /bin/bash -p agent agent \
    && echo "agent ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Configure git with global settings
RUN git config --system --add safe.directory '*' \
    && git config --system init.defaultBranch main \
    && git config --system pull.rebase false \
    && git config --system credential.helper store

# Set resource limits
COPY limits.conf /etc/security/limits.d/agent.conf

# Install helpful development aliases and tools
COPY .bashrc /home/agent/.bashrc
COPY .bash_aliases /home/agent/.bash_aliases

# Set ownership
RUN chown -R agent:agent /home/agent /workspaces

# Copy agent process files
COPY agent-process/requirements.txt /tmp/agent-requirements.txt
COPY agent-process/autonomous_agent_with_memory.py /usr/local/bin/autonomous_agent_with_memory.py
COPY agent-process/agent_memory_manager.py /usr/local/bin/agent_memory_manager.py
COPY agent-process/claude_client_with_memory.py /usr/local/bin/claude_client_with_memory.py

# Install Python dependencies for agent process (including memory system dependencies)
RUN pip3 install -r /tmp/agent-requirements.txt

# Make agent process executable
RUN chmod +x /usr/local/bin/autonomous_agent_with_memory.py

# Switch to agent user
USER agent
WORKDIR /workspaces

# Set environment variables
ENV USER=agent
ENV HOME=/home/agent
ENV SHELL=/bin/bash
ENV PYTHONPATH=/usr/local/bin:$PYTHONPATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD [ "python3", "-c", "print('Agent container healthy')" ]

# Default command starts the memory-enhanced autonomous agent
CMD ["python3", "/usr/local/bin/autonomous_agent_with_memory.py"]