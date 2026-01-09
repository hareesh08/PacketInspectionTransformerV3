#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Configuration
PROJECT_DIR="/opt/packet-inspection-transformer"
VENV_PATH="$PROJECT_DIR/venv"
DASHBOARD_PATH="$PROJECT_DIR/dashboard"
NGINX_CONFIG="/etc/nginx/sites-available/packet-inspection-transformer"
NGINX_ENABLED="/etc/nginx/sites-enabled/packet-inspection-transformer"
SYSTEMD_SERVICE="/etc/systemd/system/packet-inspection-transformer.service"
PID_FILE="/tmp/uvicorn.pid"

# Confirmation prompt
confirm_clean() {
    echo ""
    log_warn "This will remove:"
    echo "  - Virtual environment ($VENV_PATH)"
    echo "  - Frontend build ($DASHBOARD_PATH/dist)"
    echo "  - Nginx site configuration"
    echo "  - Systemd service"
    echo "  - All logs"
    echo ""
    echo -e "${RED}Model files in $PROJECT_DIR/model/ will NOT be deleted${NC}"
    echo ""
    
    read -p "Are you sure you want to continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log_info "Clean cancelled"
        exit 0
    fi
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root (use sudo)"
        exit 1
    fi
}

# Stop and disable systemd service
stop_systemd_service() {
    log_info "Stopping and disabling systemd service..."
    
    if [ -f "$SYSTEMD_SERVICE" ]; then
        systemctl stop packet-inspection-transformer 2>/dev/null || true
        systemctl disable packet-inspection-transformer 2>/dev/null || true
        rm -f "$SYSTEMD_SERVICE"
        systemctl daemon-reload
        log_success "Systemd service removed"
    else
        log_info "Systemd service not found, skipping"
    fi
}

# Kill uvicorn processes
kill_uvicorn() {
    log_info "Killing uvicorn processes..."
    
    # Kill by PID file if exists
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || true
            log_info "Killed uvicorn (PID: $PID)"
        fi
        rm -f "$PID_FILE"
    fi
    
    # Kill any remaining uvicorn processes
    pkill -f "uvicorn app:app" 2>/dev/null || true
    pkill -f "uvicorn" 2>/dev/null || true
    
    # Kill by port
    fuser -k 8000/tcp 2>/dev/null || true
    
    log_success "All uvicorn processes killed"
}

# Remove virtual environment
remove_venv() {
    log_info "Removing virtual environment..."
    
    if [ -d "$VENV_PATH" ]; then
        rm -rf "$VENV_PATH"
        log_success "Virtual environment removed"
    else
        log_info "Virtual environment not found, skipping"
    fi
}

# Remove frontend build
remove_frontend_build() {
    log_info "Removing frontend build..."
    
    if [ -d "$DASHBOARD_PATH/dist" ]; then
        rm -rf "$DASHBOARD_PATH/dist"
        log_success "Frontend build removed"
    else
        log_info "Frontend build not found, skipping"
    fi
}

# Remove nginx configuration
remove_nginx_config() {
    log_info "Removing nginx configuration..."
    
    if [ -f "$NGINX_ENABLED" ]; then
        rm -f "$NGINX_ENABLED"
    fi
    
    if [ -f "$NGINX_CONFIG" ]; then
        rm -f "$NGINX_CONFIG"
    fi
    
    # Restore default site
    if [ -f "/etc/nginx/sites-available/default.bak" ]; then
        mv /etc/nginx/sites-available/default.bak /etc/nginx/sites-available/default 2>/dev/null || true
        ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default 2>/dev/null || true
    fi
    
    # Test and reload nginx
    nginx -t 2>/dev/null && systemctl reload nginx || true
    
    log_success "Nginx configuration removed"
}

# Remove logs
remove_logs() {
    log_info "Removing logs..."
    
    if [ -d "$PROJECT_DIR/logs" ]; then
        rm -rf "$PROJECT_DIR/logs"
        mkdir -p "$PROJECT_DIR/logs"
        log_success "Logs removed (directory recreated)"
    else
        log_info "Logs directory not found, skipping"
    fi
}

# Remove systemd service file
remove_systemd_service() {
    log_info "Removing systemd service..."
    
    if [ -f "$SYSTEMD_SERVICE" ]; then
        rm -f "$SYSTEMD_SERVICE"
        systemctl daemon-reload
        log_success "Systemd service removed"
    else
        log_info "Systemd service not found, skipping"
    fi
}

# Main function
main() {
    echo "=============================================="
    echo "  Packet Inspection Transformer - Clean"
    echo "=============================================="
    echo ""
    
    check_root
    confirm_clean
    kill_uvicorn
    stop_systemd_service
    remove_frontend_build
    remove_venv
    remove_nginx_config
    remove_logs
    remove_systemd_service
    
    echo ""
    echo "=============================================="
    log_success "Clean completed successfully!"
    echo "=============================================="
    echo ""
    echo "What was removed:"
    echo "  ✓ Virtual environment"
    echo "  ✓ Frontend build"
    echo "  ✓ Nginx site configuration"
    echo "  ✓ Systemd service"
    echo "  ✓ Logs"
    echo ""
    echo "What was preserved:"
    echo "  ✓ Model files in $PROJECT_DIR/model/"
    echo ""
    echo "To reinstall, run: sudo ./setup.sh"
    echo ""
}

# Run main function
main "$@"