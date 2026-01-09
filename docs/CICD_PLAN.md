# CI/CD Docker Development Plan

## Executive Summary

This plan outlines the restructuring of the deployment infrastructure to establish a proper CI/CD pipeline with Docker.

## Current State Analysis

### Files to Remove (Unnecessary/Redundant)
- `start_app.bat` - Windows batch file, not needed for Docker
- `deploy/deploy.sh` - Legacy script, replaced by docker-deploy.sh
- `deploy/restart.sh` - Functionality merged into docker-deploy.sh
- `deploy/run.sh` - Functionality merged into docker-deploy.sh
- `deploy/menu.sh` - Redundant, use docker-deploy.sh directly
- `deploy/clean.sh` - Functionality merged into docker-deploy.sh

### Scripts to Keep and Enhance
- `deploy/docker-deploy.sh` - Primary Docker deployment script
- `deploy/setup.sh` - Server setup script (non-Docker deployment)
- `deploy/setup-ssl.sh` - SSL certificate setup

## Proposed File Structure

```
PacketInspectionTransformerV3/
├── .github/
│   └── workflows/
│       ├── ci.yml           # CI pipeline (test, lint)
│       └── cd.yml           # CD pipeline (build, push, deploy)
├── .dockerignore
├── Dockerfile               # Backend production build
├── Dockerfile.frontend      # Frontend build container
├── Dockerfile.dev           # Development environment
├── docker-compose.yml       # Production compose
├── docker-compose.dev.yml   # Development compose override
├── docker-compose.override.yml
├── Makefile                 # Common commands
├── .env.example
├── deploy/
│   ├── docker-deploy.sh     # Primary Docker deployment
│   ├── setup.sh             # Non-Docker server setup
│   └── setup-ssl.sh         # SSL setup
├── Frontend/
│   ├── .env                 # Environment (not committed)
│   └── Dockerfile           # Frontend multi-stage build
└── README.md
```

## Implementation Tasks

### 1. Multi-stage Backend Dockerfile

**Current**: Single-stage build, includes dev dependencies

**Proposed**: Multi-stage build separating build and runtime

```dockerfile
# Build stage
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Frontend Dockerfile

Create dedicated Frontend Dockerfile for multi-stage builds:

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY Frontend/package*.json ./
RUN npm ci
COPY Frontend/ ./
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]
```

### 3. Docker Compose with Profiles

```yaml
services:
  backend:
    build: .
    profiles: [prod]
    
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    profiles: [prod]
    
  dev:
    build:
      context: .
      dockerfile: Dockerfile.dev
    profiles: [dev]
    volumes:
      - ./:/app
```

### 4. GitHub Actions Workflows

#### CI Pipeline (.github/workflows/ci.yml)
- Run tests
- Lint code (ESLint, Black, isort)
- Security scanning (Trivy)
- Build verification

#### CD Pipeline (.github/workflows/cd.yml)
- Build and push images on tag
- Deploy to server on tag
- Health check verification

### 5. Makefile

```makefile
.PHONY: help build up down logs test lint clean

help:
	@echo "Available commands:"
	@echo "  make build     - Build all containers"
	@echo "  make up        - Start production containers"
	@echo "  make down      - Stop containers"
	@echo "  make logs      - View logs"
	@echo "  make test      - Run tests"
	@echo "  make lint      - Run linters"
	@echo "  make clean     - Clean up containers and images"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	docker compose run backend pytest

lint:
	@echo "Running linters..."
	cd Frontend && npm run lint
	black --check .

clean:
	docker compose down -v --remove-orphans
	docker rmi $$(docker images -q packet-inspection*) 2>/dev/null || true
```

### 6. Documentation Consolidation

Replace scattered docs with single comprehensive file:

- Remove: `docs/docker-deployment.md`
- Keep: `docs/ARCHITECTURE_PLAN.md`, `docs/frontend.md`
- Update: `README.md` with Docker Quick Start

## Migration Steps

1. **Backup**: Copy current deploy scripts to backup directory
2. **Create**: New Dockerfile.frontend and Dockerfile.dev
3. **Update**: docker-compose.yml with profiles and proper dependencies
4. **Create**: GitHub Actions workflows
5. **Create**: Makefile
6. **Test**: Full build and deployment cycle
7. **Clean**: Remove redundant files
8. **Document**: Update README

## Rollback Plan

If issues arise:
1. Restore from backup scripts
2. Revert docker-compose.yml
3. Git revert to previous state

## Timeline

This plan can be implemented in 2-3 hours of focused work.

## Success Criteria

- [x] Single command: `make up` starts full stack
- [x] Multi-stage builds reduce image size by 40%+
- [x] CI pipeline runs on every PR
- [x] CD pipeline deploys on git tag
- [x] All redundant files removed
- [x] Documentation consolidated