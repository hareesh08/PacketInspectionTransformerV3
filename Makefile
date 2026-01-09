# ============================================================================
# Packet Inspection Transformer - Makefile
# ============================================================================
# Common commands for development and deployment
#
# Usage:
#   make help          - Show available commands
#   make build         - Build all containers
#   make up            - Start production containers
#   make up-dev        - Start development container
#   make down          - Stop containers
#   make logs          - View logs
#   make test          - Run tests
#   make lint          - Run linters
#   make clean         - Clean up containers and images
# ============================================================================

.PHONY: help build up up-dev down logs test lint clean build-frontend

# Default target
help:
	@echo ""
	@echo "Packet Inspection Transformer - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make up-dev       - Start development environment with hot reload"
	@echo "  make build-frontend - Build frontend for production"
	@echo "  make test         - Run backend tests"
	@echo "  make lint         - Run linters (frontend + backend)"
	@echo ""
	@echo "Production:"
	@echo "  make build        - Build all production containers"
	@echo "  make up           - Start production containers"
	@echo "  make down         - Stop all containers"
	@echo "  make logs         - View logs (follow mode)"
	@echo "  make status       - Show container status"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean        - Remove all containers, images, and volumes"
	@echo "  make prune        - Remove unused Docker resources"
	@echo "  make restart      - Restart all containers"
	@echo ""
	@echo "Server Deployment:"
	@echo "  make deploy       - Deploy to production server (requires SSH)"
	@echo ""

# ----------------------------------------------------------------------------
# Development Commands
# ----------------------------------------------------------------------------

up-dev:
	@echo "Starting development environment..."
	docker compose --profile dev up -d
	@echo ""
	@echo "Development server running at http://localhost:8001"
	@echo "Hot reload enabled - changes will be reflected automatically"

build-frontend:
	@echo "Building frontend..."
	cd Frontend && npm ci --quiet && npm run build
	@echo "Frontend built successfully"

test:
	@echo "Running backend tests..."
	docker compose run --rm backend pytest tests/ -v

lint:
	@echo "Running linters..."
	@echo "Frontend lint..."
	cd Frontend && npm run lint || true
	@echo ""
	@echo "Backend lint (black, isort)..."
	@command -v black >/dev/null 2>&1 || pip install black isort
	black --check . || true
	isort --check-only . || true

# ----------------------------------------------------------------------------
# Production Commands
# ----------------------------------------------------------------------------

build:
	@echo "Building production containers..."
	docker compose build

up:
	@echo "Starting production environment..."
	docker compose --profile prod up -d
	@echo ""
	@echo "Production server running at http://localhost"
	@echo "API available at http://localhost/api"

down:
	@echo "Stopping all containers..."
	docker compose down

logs:
	@echo "Viewing logs (Ctrl+C to exit)..."
	docker compose logs -f

status:
	@echo "Container Status:"
	docker compose ps
	@echo ""
	@echo "Health Check:"
	@curl -s http://localhost/health && echo " - OK" || echo " - FAILED"

restart:
	@echo "Restarting all containers..."
	docker compose restart

# ----------------------------------------------------------------------------
# Maintenance Commands
# ----------------------------------------------------------------------------

clean:
	@echo "WARNING: This will remove all containers, images, and volumes!"
	@read -p "Continue? (yes/no): " confirm && \
	if [ "$$confirm" = "yes" ]; then \
		docker compose down -v --remove-orphans; \
		docker rmi $$(docker images -q packet-inspection* 2>/dev/null) 2>/dev/null || true; \
		echo "Cleanup complete!"; \
	else \
		echo "Cancelled"; \
	fi

prune:
	@echo "Removing unused Docker resources..."
	docker system prune -f
	docker image prune -f
	@echo "Prune complete!"

# ----------------------------------------------------------------------------
# Deployment Commands
# ----------------------------------------------------------------------------

deploy:
	@echo "Deploying to production server..."
	@if [ -z "$(SERVER)" ]; then \
		echo "Error: SERVER not set. Usage: make deploy SERVER=user@host"; \
		exit 1; \
	fi
	@echo "Deploying to $(SERVER)..."
	ssh -o StrictHostKeyChecking=no $(SERVER) << 'EOF'
		cd /opt/packet-inspection-transformer
		git pull
		docker compose down
		docker compose pull
		docker compose --profile prod up -d
		docker image prune -f
		echo "Deployment complete!"
	EOF
	@echo "Health check..."
	sleep 5
	curl -f http://localhost/health && echo " - OK" || echo " - FAILED"