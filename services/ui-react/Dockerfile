# Build stage
FROM node:20-bullseye as dependencies

WORKDIR /app

# Copy package files first (better caching)
COPY package*.json ./

# Install dependencies with caching optimizations
RUN npm install --legacy-peer-deps --prefer-offline --no-audit --no-fund

# Build stage
FROM dependencies as build

# Copy source code
COPY . .

# Build the app (only if not in development mode)
RUN if [ "$NODE_ENV" != "development" ]; then npm run build; fi

# Production stage (static files)
FROM nginx:alpine as production

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built app from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

# Development stage (live source code)
FROM build as development

# Expose port for Vite dev server
EXPOSE 3000

# Health check for development server
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Start development server with source code (unminified, hot reload)
CMD ["npm", "start"]