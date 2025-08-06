FROM fuzeagent/dev-base:latest

# Install Python and development tools
RUN sudo apt-get update && sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    python3-wheel \
    python3-setuptools \
    # Python build dependencies  
    build-essential \
    libffi-dev \
    libssl-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev \
    # Database drivers
    libpq-dev \
    # Other useful tools
    sqlite3 \
    && sudo rm -rf /var/lib/apt/lists/*

# Create symlink for python command
RUN sudo ln -sf /usr/bin/python3 /usr/bin/python

# Upgrade pip and install essential Python tools
RUN python -m pip install --upgrade pip setuptools wheel

# Install common Python development packages
RUN python -m pip install \
    # Core web frameworks
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    # Database and ORM
    sqlalchemy==2.0.23 \
    alembic==1.12.1 \
    asyncpg==0.29.0 \
    # HTTP clients
    httpx==0.25.2 \
    requests==2.31.0 \
    # Data validation
    pydantic==2.5.0 \
    # Testing frameworks
    pytest==7.4.3 \
    pytest-asyncio==0.21.1 \
    pytest-cov==4.1.0 \
    # Code quality
    black==23.11.0 \
    isort==5.12.0 \
    mypy==1.7.1 \
    flake8==6.1.0 \
    pylint==3.0.3 \
    # Documentation
    mkdocs==1.5.3 \
    mkdocs-material==9.4.8 \
    # Jupyter for interactive development
    jupyter==1.0.0 \
    ipython==8.17.2 \
    # Task queue and async tools
    celery==5.3.4 \
    redis==5.0.1 \
    # Utilities
    click==8.1.7 \
    python-dotenv==1.0.0 \
    pyyaml==6.0.1 \
    # CrewAI for agent orchestration
    crewai==0.28.8 \
    # AI/LLM tools
    anthropic==0.7.8 \
    openai==1.3.7

# Install development configuration files
COPY pyproject.toml /home/agent/pyproject.toml
COPY .python-version /home/agent/.python-version

# Set up Python virtual environment in workspace
RUN python -m venv /home/agent/.venv \
    && echo "source /home/agent/.venv/bin/activate" >> /home/agent/.bashrc

# Python-specific aliases
COPY .python_aliases /home/agent/.python_aliases
RUN echo "source /home/agent/.python_aliases" >> /home/agent/.bashrc

# Set Python environment variables
ENV PYTHONPATH="/workspaces:$PYTHONPATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_USER=1

# Set ownership
RUN sudo chown -R agent:agent /home/agent

USER agent
WORKDIR /workspaces

# Welcome message override
RUN echo 'echo "🐍 FuzeAgent Python Development Container"' >> /home/agent/.bashrc \
    && echo 'echo "   Python: $(python --version)"' >> /home/agent/.bashrc \
    && echo 'echo "   Virtual Env: ~/.venv"' >> /home/agent/.bashrc \
    && echo 'echo "   FastAPI, SQLAlchemy, pytest ready"' >> /home/agent/.bashrc