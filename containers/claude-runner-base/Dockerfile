# syntax=docker/dockerfile:1
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl wget git ca-certificates gnupg \
    python3.12 python3.12-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*

# Claude Code SDK — no auth needed (public npm)
RUN npm install -g @anthropic-ai/claude-code

# repo-digester from FuzePlan GitHub Packages.
# Token mounted as a BuildKit secret — NEVER stored in any image layer or metadata.
RUN --mount=type=secret,id=npm_token \
    NPM_TOKEN=$(cat /run/secrets/npm_token) && \
    echo "@izzywdev:registry=https://npm.pkg.github.com" > /tmp/.npmrc-gh && \
    echo "@fuzefront:registry=https://npm.pkg.github.com" >> /tmp/.npmrc-gh && \
    echo "//npm.pkg.github.com/:_authToken=${NPM_TOKEN}" >> /tmp/.npmrc-gh && \
    npm --userconfig /tmp/.npmrc-gh install -g @izzywdev/repo-digester 2>/dev/null || \
    echo "repo-digester not yet published, skipping" && \
    rm -f /tmp/.npmrc-gh

COPY session-relay.sh /usr/local/bin/session-relay
RUN chmod +x /usr/local/bin/session-relay

WORKDIR /workspace
ENV ANTHROPIC_API_KEY=""
ENV WS_RELAY_URL=""
ENV AGENT_ID=""

CMD ["/usr/local/bin/session-relay"]
