# syntax=docker/dockerfile:1
FROM ghcr.io/izzywdev/fuzeagent/claude-runner-base:latest
USER root
RUN apt-get update && apt-get install -y pandoc && rm -rf /var/lib/apt/lists/*
RUN npm install -g puppeteer cheerio
USER agent
CMD ["/usr/local/bin/session-relay"]
