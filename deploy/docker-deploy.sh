#!/bin/bash
set -e

# ============================================================================
# Packet Inspection Transformer - Docker Deployment Script
# ============================================================================
# Usage:
#   ./docker-deploy.sh build    - Build Docker images
#   ./docker-deploy.sh up       - Start containers
#   ./docker-deploy.sh down     - Stop containers
#   ./docker-deploy.sh restart  - Restart containers
#   ./docker-deploy.sh logs     - View logs
#   ./docker-deploy.sh status   - Check container status
#   ./docker-deploy.sh clean    - Remove containers and images
# ============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    if ! docker ps &> /dev/null; then
        log_error "Docker daemon is not running."
        exit 1
    fi
}

build_frontend() {
    log_info "Building frontend..."
    
    if [ ! -d "Frontend" ]; then
        log_warn "Frontend directory not found"
        return
    fi
    
    cd Frontend
    npm ci --quiet 2>/dev/null || npm install --quiet
    npm run build
    
    mkdir -p ../dashboard/dist
    mv dist/* ../dashboard/dist/
    cd ..
    
    log_success "Frontend built"
}

do_build() {
    log_info "Building Docker images..."
    
    # Build frontend first
    build_frontend
    
    # Build Docker images
    docker compose build
    
    log_success "Docker images built"
}

do_up() {
    log_info "Starting containers..."
    docker compose up -d
    log_success "Containers started"
    do_status
}

do_down() {
    log_info "Stopping containers..."
    docker compose down
    log_success "Containers stopped"
}

do_restart() {
    log_info "Restarting containers..."
    docker compose restart
    log_success "Containers restarted"
    do_status
}

do_logs() {
    log_info "Showing logs (Ctrl+C to exit)..."
    docker compose logs -f
}

do_status() {
    echo ""
    echo "Container Status:"
    docker compose ps
    echo ""
    echo "Health Check:"
    curl -s http://localhost/health && echo " - OK" || echo " - FAILED"
    echo ""
}

do_clean() {
    log_warn "This will remove all Docker containers and images for this project!"
    read -p "Continue? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        docker compose down -v --remove-orphans
        docker rmi packet-inspection-transformer-backend packet-inspection-transformer-nginx 2>/dev/null || true
        log_success "Cleaned up"
    else
        log_info "Cancelled"
    fi
}

show_help() {
    echo "Packet Inspection Transformer - Docker Deployment"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  build    - Build images and frontend"
    echo "  up       - Start containers (detached)"
    echo "  down     - Stop containers"
    echo "  restart  - Restart containers"
    echo "  logs     - View logs (follow mode)"
    echo "  status   - Show container status"
    echo "  clean    - Remove all containers and images"
    echo ""
}

main() {
    check_docker
    
    command="${1:-help}"
    
    case "$command" in
        build)   do_build ;;
        up)      do_up ;;
        down)    do_down ;;
        restart) do_restart ;;
        logs)    do_logs ;;
        status)  do_status ;;
        clean)   do_clean ;;
        help|--help|-h) show_help ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"