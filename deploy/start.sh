#!/bin/bash

# =============================================================================
# Malware Detection Gateway - Main Deployment Script
# =============================================================================
# Usage: ./start.sh [command]
# Commands:
#   fresh    - Fresh install with dependencies and start services
#   restart  - Restart all services
#   stop     - Stop all services
#   clean    - Clean cache and temporary files
#   status   - Check service status
#   logs     - Show service logs
# =============================================================================

set -e  # Exit on any error

# Configuration
PROJECT_NAME="Malware Detection Gateway"
BACKEND_PORT=8000
FRONTEND_PORT=80
NGINX_CONFIG_NAME="malware-detection"

# Get absolute paths at script start
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/Frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function to source NVM
source_nvm() {
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root for certain operations
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. This is required for nginx and port 80 operations."
    fi
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    # Update system
    apt update && apt upgrade -y
    
    # Install Python and pip
    apt install -y python3 python3-pip python3-venv python3-dev
    
    # Install NVM and Node.js
    install_nodejs_with_nvm
    
    # Install nginx
    apt install -y nginx
    
    # Install other utilities
    apt install -y curl wget git htop unzip software-properties-common
    
    log_success "System dependencies installed"
}

# Install Node.js using NVM
install_nodejs_with_nvm() {
    log_info "Installing Node.js using NVM..."
    
    # Install NVM (latest version)
    log_info "Installing NVM..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    
    # Source NVM to make it available in current session
    source_nvm
    
    # Install latest LTS Node.js
    log_info "Installing Node.js LTS..."
    nvm install --lts
    nvm use --lts
    nvm alias default lts/*
    
    # Verify installation
    log_info "Node.js version: $(node -v)"
    log_info "NPM version: $(npm -v)"
    
    log_success "Node.js installed successfully via NVM"
}

# Install Python dependencies
install_python_deps() {
    log_info "Installing Python dependencies..."
    
    cd "$PROJECT_ROOT"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_info "Created Python virtual environment"
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_success "Python dependencies installed"
}

# Install Node.js dependencies
install_node_deps() {
    log_info "Installing Node.js dependencies..."
    
    # Source NVM to ensure Node.js is available
    source_nvm
    
    cd "$FRONTEND_DIR"
    
    # Install dependencies
    npm install
    
    # Install global packages
    npm install -g serve pm2
    
    log_success "Node.js dependencies installed"
}

# Build frontend
build_frontend() {
    log_info "Building frontend..."
    
    # Source NVM to ensure Node.js is available
    source_nvm
    
    log_info "Script directory: $SCRIPT_DIR"
    log_info "Project root: $PROJECT_ROOT"
    log_info "Frontend directory: $FRONTEND_DIR"
    
    if [ ! -d "$FRONTEND_DIR" ]; then
        log_error "Frontend directory not found at: $FRONTEND_DIR"
        ls -la "$PROJECT_ROOT" 2>/dev/null || true
        return 1
    fi
    
    cd "$FRONTEND_DIR"
    
    # Build for production
    npm run build
    
    log_success "Frontend built successfully"
}

# Setup nginx configuration
setup_nginx() {
    log_info "Setting up nginx configuration..."
    
    # Copy nginx configuration using absolute path
    cp "$SCRIPT_DIR/nginx.conf" "/etc/nginx/sites-available/$NGINX_CONFIG_NAME"
    
    # Enable site
    ln -sf "/etc/nginx/sites-available/$NGINX_CONFIG_NAME" "/etc/nginx/sites-enabled/$NGINX_CONFIG_NAME"
    
    # Remove default nginx site
    rm -f /etc/nginx/sites-enabled/default
    
    # Ensure frontend is accessible - copy dist files to nginx html directory
    if [ -d "$FRONTEND_DIR/dist" ]; then
        mkdir -p "/var/www/$NGINX_CONFIG_NAME/html"
        cp -r "$FRONTEND_DIR/dist/"* "/var/www/$NGINX_CONFIG_NAME/html/"
        log_info "Frontend files copied to /var/www/$NGINX_CONFIG_NAME/html"
    fi
    
    # Test nginx configuration
    nginx -t
    
    log_success "Nginx configuration setup complete"
}

# Start backend service
start_backend() {
    log_info "Starting backend service..."
    
    cd "$PROJECT_ROOT"
    
    # Create necessary directories
    mkdir -p logs data model
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Set environment variables
    export ENVIRONMENT=production
    export DEBUG=false
    export LOG_LEVEL=info
    export HOST=0.0.0.0
    export PORT=$BACKEND_PORT
    
    # Start backend with PM2
    pm2 start app.py --name "malware-backend" --interpreter python3 || pm2 restart malware-backend
    
    log_success "Backend service started on port $BACKEND_PORT"
}

# Start frontend service
start_frontend() {
    log_info "Starting frontend service..."
    
    # Source NVM to ensure Node.js is available
    source_nvm
    
    cd "$FRONTEND_DIR"
    
    # Start frontend with PM2 (serve the built files)
    pm2 start "serve -s dist -l 3000" --name "malware-frontend" || pm2 restart malware-frontend
    
    log_success "Frontend service started on port 3000"
}

# Start nginx
start_nginx() {
    log_info "Starting nginx..."
    
    systemctl enable nginx
    systemctl start nginx
    systemctl reload nginx
    
    log_success "Nginx started and configured"
}

# Stop all services
stop_services() {
    log_info "Stopping all services..."
    
    # Stop PM2 processes
    pm2 stop malware-backend malware-frontend 2>/dev/null || true
    pm2 delete malware-backend malware-frontend 2>/dev/null || true
    
    # Stop nginx
    systemctl stop nginx 2>/dev/null || true
    
    log_success "All services stopped"
}

# Clean cache and temporary files
clean_cache() {
    log_info "Cleaning cache and temporary files..."
    
    # Clean Python cache
    find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null || true
    
    # Clean Node.js cache
    cd "$FRONTEND_DIR"
    npm cache clean --force 2>/dev/null || true
    rm -rf node_modules/.cache 2>/dev/null || true
    rm -rf dist 2>/dev/null || true
    
    # Clean logs
    cd "$PROJECT_ROOT"
    rm -rf logs/*.log 2>/dev/null || true
    
    # Clean PM2 logs
    pm2 flush 2>/dev/null || true
    
    log_success "Cache and temporary files cleaned"
}

# Check service status
check_status() {
    log_info "Checking service status..."
    echo
    
    # Check backend
    echo "=== Backend Status ==="
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null; then
        log_success "Backend is running (http://localhost:$BACKEND_PORT)"
    else
        log_error "Backend is not responding"
    fi
    
    # Check frontend via nginx
    echo
    echo "=== Frontend Status ==="
    if curl -s http://localhost/ > /dev/null; then
        log_success "Frontend is accessible via nginx (http://localhost)"
    else
        log_error "Frontend is not accessible"
    fi
    
    # Check nginx
    echo
    echo "=== Nginx Status ==="
    if systemctl is-active --quiet nginx; then
        log_success "Nginx is running"
    else
        log_error "Nginx is not running"
    fi
    
    # Check PM2 processes
    echo
    echo "=== PM2 Processes ==="
    pm2 list
    
    # Check ports
    echo
    echo "=== Port Usage ==="
    echo "Port $BACKEND_PORT (Backend):"
    lsof -i :$BACKEND_PORT 2>/dev/null || echo "  No processes found"
    echo "Port $FRONTEND_PORT (Nginx):"
    lsof -i :$FRONTEND_PORT 2>/dev/null || echo "  No processes found"
    
    # Show public IP
    echo
    echo "=== External Access ==="
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "Unable to detect")
    echo "Public IP: $PUBLIC_IP"
    echo "Frontend URL: http://$PUBLIC_IP"
    echo "Backend API: http://$PUBLIC_IP/api"
}

# Show logs
show_logs() {
    log_info "Showing service logs..."
    echo
    
    echo "=== PM2 Logs ==="
    pm2 logs --lines 50
    
    echo
    echo "=== Nginx Error Logs ==="
    tail -n 20 /var/log/nginx/error.log 2>/dev/null || echo "No nginx error logs found"
    
    echo
    echo "=== Nginx Access Logs ==="
    tail -n 20 /var/log/nginx/access.log 2>/dev/null || echo "No nginx access logs found"
}

# Fresh installation
fresh_install() {
    log_info "Starting fresh installation of $PROJECT_NAME..."
    
    check_root
    
    install_system_deps
    install_python_deps
    install_node_deps
    build_frontend
    setup_nginx
    
    log_info "Starting services..."
    start_backend
    start_frontend
    start_nginx
    
    # Wait a moment for services to start
    sleep 5
    
    check_status
    
    log_success "Fresh installation completed!"
    echo
    echo "=== Access Information ==="
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "your-server-ip")
    echo "Frontend: http://$PUBLIC_IP"
    echo "Backend API: http://$PUBLIC_IP/api"
    echo "Health Check: http://$PUBLIC_IP/api/health"
}

# Restart services
restart_services() {
    log_info "Restarting all services..."
    
    stop_services
    sleep 2
    
    start_backend
    start_frontend
    start_nginx
    
    sleep 3
    check_status
    
    log_success "All services restarted"
}

# Main script logic
case "${1:-}" in
    "fresh")
        fresh_install
        ;;
    "restart")
        restart_services
        ;;
    "stop")
        stop_services
        ;;
    "clean")
        clean_cache
        ;;
    "status")
        check_status
        ;;
    "logs")
        show_logs
        ;;
    *)
        echo "Usage: $0 {fresh|restart|stop|clean|status|logs}"
        echo
        echo "Commands:"
        echo "  fresh    - Fresh install with dependencies and start services"
        echo "  restart  - Restart all services"
        echo "  stop     - Stop all services"
        echo "  clean    - Clean cache and temporary files"
        echo "  status   - Check service status"
        echo "  logs     - Show service logs"
        echo
        echo "Examples:"
        echo "  sudo ./start.sh fresh     # First time setup"
        echo "  sudo ./start.sh restart   # Restart services"
        echo "  ./start.sh status         # Check status"
        exit 1
        ;;
esac