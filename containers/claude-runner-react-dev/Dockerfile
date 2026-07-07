# syntax=docker/dockerfile:1
FROM ghcr.io/izzywdev/fuzeagent/claude-runner-base:latest
RUN npm install -g vite typescript eslint prettier @vitejs/plugin-react create-vite
CMD ["/usr/local/bin/session-relay"]
