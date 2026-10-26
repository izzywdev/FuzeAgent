# syntax=docker/dockerfile:1
# Build stage
FROM node:24-alpine AS dependencies

WORKDIR /app

# Copy package files + npm registry config first (better caching).
# .npmrc maps the @izzywdev/* scope to GitHub Packages -- services/ui-react
# depends on @izzywdev/fuzefront-identity -- and reads its auth token from
# $GITHUB_TOKEN. See .npmrc for the full rationale.
COPY package*.json .npmrc ./

# Install dependencies with caching optimizations.
# Token mounted as a BuildKit secret -- NEVER stored in any image layer or
# metadata (matches containers/claude-runner-base/Dockerfile's npm_token
# pattern). A build-arg would bake it into the image history instead.
RUN --mount=type=secret,id=github_token \
    export GITHUB_TOKEN="$(cat /run/secrets/github_token)" && \
    npm ci --legacy-peer-deps --prefer-offline --no-audit --no-fund

# Build stage
FROM dependencies AS build

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built app from build stage to both root and /apps/fuzeagent
COPY --from=build /app/dist /usr/share/nginx/html
COPY --from=build /app/dist /usr/share/nginx/html/apps/fuzeagent

# Ensure remoteEntry.js is always reachable at /apps/fuzeagent/remoteEntry.js even if bundled under assets
RUN if [ -f /usr/share/nginx/html/apps/fuzeagent/assets/remoteEntry.js ] && [ ! -f /usr/share/nginx/html/apps/fuzeagent/remoteEntry.js ]; then \
      cp /usr/share/nginx/html/apps/fuzeagent/assets/remoteEntry.js /usr/share/nginx/html/apps/fuzeagent/remoteEntry.js; \
    fi


# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Expose port
EXPOSE 3000

# Start nginx
CMD ["nginx", "-g", "daemon off;"]