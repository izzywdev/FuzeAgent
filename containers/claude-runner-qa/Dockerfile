# syntax=docker/dockerfile:1
FROM ghcr.io/izzywdev/fuzeagent/claude-runner-base:latest
USER root
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2t64 \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g @playwright/test
USER agent
CMD ["/usr/local/bin/session-relay"]
