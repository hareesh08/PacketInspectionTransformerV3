#!/bin/bash
set -e

# ============================================================================
# Packet Inspection Transformer - Docker Deployment Script
# ============================================================================
# Usage:
#   ./docker-deploy.sh install  - Install Docker (if not present)
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

# Install Docker and Docker Compose if not present
install_docker() {
    log_info "Installing Docker and Docker Compose..."
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log_warn "Not running as root, will use sudo"
        SUDO="sudo"
    else
        SUDO=""
    fi
    
    # Install dependencies
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq curl ca-certificates gnupg lsb-release
    
    # Install Docker
    if ! command -v docker &> /dev/null; then
        log_info "Installing Docker Engine..."
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | $SUDO gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null
        $SUDO apt-get update -qq
        $SUDO apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
        $SUDO usermod -aG docker $USER
        log_success "Docker installed successfully"
    else
        log_success "Docker is already installed"
    fi
    
    # Install Docker Compose v2
    if ! docker compose version &> /dev/null; then
        log_info "Installing Docker Compose..."
        $SUDO curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
        $SUDO chmod +x /usr/local/bin/docker-compose
        log_success "Docker Compose installed"
    else
        log_success "Docker Compose is already installed"
    fi
    
    # Start Docker daemon if not running
    if ! pgrep -x dockerd > /dev/null; then
        log_info "Starting Docker daemon..."
        $SUDO service docker start
    fi
    
    log_success "Docker installation completed"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Run './docker-deploy.sh install' to install it."
        exit 1
    fi
    if ! docker ps &> /dev/null; then
        log_error "Docker daemon is not running. Run 'sudo service docker start'."
        exit 1
    fi
}

build_frontend() {
    log_info "Building frontend..."
    
    if [ ! -d "Frontend" ]; then
        log_warn "Frontend directory not found"
        return
    fi
    
    # Check if npm is installed, install if not
    if ! command -v npm &> /dev/null; then
        log_info "Installing Node.js and npm..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash
        apt-get install -y nodejs
    fi
    
    cd Frontend
    
    # Clear vite cache to fix stale imports
    rm -rf node_modules/.vite 2>/dev/null || true
    
    npm ci --quiet 2>/dev/null || npm install --quiet
    npm run build
    
    # Clean and rebuild dashboard directory
    rm -rf ../dashboard/dist
    mkdir -p ../dashboard/dist
    cp -r dist/* ../dashboard/dist/
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
    command="${1:-help}"
    
    # install command doesn't require docker to be running
    if [ "$command" = "install" ]; then
        install_docker
        exit 0
    fi
    
    check_docker
    
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