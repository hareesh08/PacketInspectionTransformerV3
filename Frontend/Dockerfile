# =============================================================================
# Packet Inspection Transformer - Frontend Dockerfile
# =============================================================================
# Production-ready multi-stage build for React frontend
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Build the React frontend
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Set environment variables for build
ENV NODE_ENV=production \
    npm_config_loglevel=warn

# Copy package files first for better caching
COPY Frontend/package*.json ./

# Install dependencies (use npm install for better compatibility)
RUN npm install --quiet --no-audit

# Copy source code (must be after npm install to leverage cache)
COPY Frontend/ .

# Build the application
# Build with production mode to minimize bundle size
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Production - Serve with Nginx
# -----------------------------------------------------------------------------
FROM nginx:alpine AS production

# Install curl for health check (using apk for Alpine)
RUN apk add --no-cache curl ca-certificates

# Set environment variables
ENV NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx/conf.d

# Copy nginx configuration
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/conf.d/ /etc/nginx/conf.d/

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create directories for certificates and logs
RUN mkdir -p /etc/nginx/certificates /var/log/nginx /var/cache/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/log/nginx /var/cache/nginx /var/run/nginx.pid /etc/nginx/certificates

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

# Labels for container metadata
LABEL maintainer="security-team" \
      version="1.0.0" \
      description="Packet Inspection Transformer Frontend" \
      org.opencontainers.image.source="https://github.com/your-org/packet-inspection-transformer"