# syntax=docker/dockerfile:1
FROM ghcr.io/izzywdev/fuzeagent/claude-runner-base:latest
RUN apt-get update && apt-get install -y python3-pip build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages pytest black ruff poetry ipython
CMD ["/usr/local/bin/session-relay"]
