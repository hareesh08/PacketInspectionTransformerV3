# ============================================================================
# Packet Inspection Transformer - Frontend Multi-Stage Dockerfile
# ============================================================================

# ----------------------------------------------------------------------------
# Build Stage: Build the React frontend
# ----------------------------------------------------------------------------
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY Frontend/package*.json ./

# Install dependencies
RUN npm ci --quiet

# Copy source code
COPY Frontend/ .

# Build the application
# Build with production mode to minimize bundle size
RUN npm run build

# ----------------------------------------------------------------------------
# Production Stage: Serve with Nginx
# ----------------------------------------------------------------------------
FROM nginx:alpine AS production

# Copy nginx configuration from root directory
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]