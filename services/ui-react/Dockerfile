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

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built app from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Expose port
EXPOSE 3000

# Start nginx
CMD ["nginx", "-g", "daemon off;"]