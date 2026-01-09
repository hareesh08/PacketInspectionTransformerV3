#!/bin/bash
set -e

# ============================================================================
# Packet Inspection Transformer - Unified Deployment Script
# ============================================================================
# Features:
# - Runs in background even after SSH disconnect
# - Skips already-installed dependencies
# - All-in-one setup, run, restart, clean operations
# ============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Configuration
PROJECT_DIR="/opt/packet-inspection-transformer"
VENV_PATH="$PROJECT_DIR/venv"
DASHBOARD_PATH="$PROJECT_DIR/dashboard"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="/tmp/uvicorn.pid"
SYSTEMD_SERVICE="/etc/systemd/system/packet-inspection-transformer.service"
NGINX_CONFIG="/etc/nginx/sites-available/packet-inspection-transformer"

# ============================================================================
# Logging Functions
# ============================================================================
log_info() { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }

# ============================================================================
# Utility Functions
# ============================================================================
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root (use sudo)"
        exit 1
    fi
}

get_server_ip() {
    hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost"
}

# ============================================================================
# Cleanup Functions
# ============================================================================
stop_services() {
    log_info "Stopping services..."
    systemctl stop packet-inspection-transformer 2>/dev/null || true
    pkill -f "uvicorn app:app" 2>/dev/null || true
    pkill -f "uvicorn" 2>/dev/null || true
    fuser -k 8000/tcp 2>/dev/null || true
    rm -f "$PID_FILE"
    log_success "Services stopped"
}

clean_all() {
    log_info "Cleaning all installations..."
    
    stop_services
    
    # Remove virtual environment
    if [ -d "$VENV_PATH" ]; then
        rm -rf "$VENV_PATH"
        log_info "Virtual environment removed"
    fi
    
    # Remove systemd service
    if [ -f "$SYSTEMD_SERVICE" ]; then
        rm -f "$SYSTEMD_SERVICE"
        systemctl daemon-reload
        log_info "Systemd service removed"
    fi
    
    # Remove Python packages
    apt-get remove -y --purge python3 python3-venv python3-pip 2>/dev/null || true
    
    # Remove Node.js
    apt-get remove -y --purge nodejs 2>/dev/null || true
    rm -f /etc/apt/sources.list.d/nodesource.list 2>/dev/null || true
    
    # Clean up
    apt-get autoremove -y -qq 2>/dev/null || true
    apt-get autoclean -qq 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# ============================================================================
# Installation Functions
# ============================================================================
update_system() {
    log_info "Updating system packages..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get upgrade -y -qq
    log_success "System updated"
}

install_python() {
    log_info "Installing Python 3..."
    apt-get install -y -qq python3 python3-venv python3-pip curl wget git
    python3 --version
    log_success "Python 3 installed"
}

install_nodejs() {
    log_info "Installing Node.js 20.x..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -E -
    apt-get install -y -qq nodejs
    node --version
    npm --version
    log_success "Node.js 20.x installed"
}

install_nginx() {
    log_info "Installing Nginx..."
    apt-get install -y -qq nginx
    systemctl enable nginx
    systemctl start nginx
    log_success "Nginx installed and started"
}

install_certbot() {
    log_info "Installing certbot..."
    apt-get install -y -qq certbot python3-certbot-nginx
    log_success "Certbot installed"
}

create_directories() {
    log_info "Creating project directories..."
    mkdir -p "$PROJECT_DIR"/{model,logs,dashboard}
    
    # Copy project files to /opt/ if running from a different directory
    CURRENT_DIR=$(pwd)
    
    # Handle running from deploy/ directory
    if [ -f "../app.py" ]; then
        log_info "Copying project files from $CURRENT_DIR/.. to $PROJECT_DIR..."
        cp -r "$CURRENT_DIR"/../* "$PROJECT_DIR/" 2>/dev/null || true
    elif [ "$CURRENT_DIR" != "$PROJECT_DIR" ] && [ -f "app.py" ]; then
        log_info "Copying project files from $CURRENT_DIR to $PROJECT_DIR..."
        cp -r "$CURRENT_DIR"/* "$PROJECT_DIR/" 2>/dev/null || true
    fi
    
    log_success "Directories created"
}

setup_venv() {
    log_info "Setting up Python virtual environment..."
    
    if [ ! -d "$VENV_PATH" ]; then
        python3 -m venv "$VENV_PATH"
        log_success "Virtual environment created"
    else
        log_info "Virtual environment exists, installing dependencies..."
    fi
    
    source "$VENV_PATH/bin/activate"
    pip install --upgrade pip -q
    
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        pip install -r "$PROJECT_DIR/requirements.txt" -q
        log_success "Python dependencies installed"
    else
        pip install fastapi uvicorn python-multipart aiofiles -q
        log_success "Core Python dependencies installed"
    fi
    deactivate
}

build_frontend() {
    log_info "Building frontend..."
    
    FRONTEND_PATH="$PROJECT_DIR/Frontend"
    
    if [ ! -d "$FRONTEND_PATH" ]; then
        log_warn "Frontend directory not found, skipping build"
        return
    fi
    
    if [ -d "$DASHBOARD_PATH/dist" ]; then
        log_info "Frontend already built, skipping"
        return
    fi
    
    cd "$FRONTEND_PATH"
    
    if [ ! -d "node_modules" ]; then
        npm ci --quiet 2>/dev/null || npm install --quiet
    fi
    
    npm run build
    
    rm -rf "$DASHBOARD_PATH/dist"
    mv dist "$DASHBOARD_PATH/dist"
    
    cd "$PROJECT_DIR"
    log_success "Frontend built"
}

create_nginx_config() {
    log_info "Creating Nginx configuration..."
    
    SERVER_IP=$(get_server_ip)
    
    cat > "$NGINX_CONFIG" << EOF
server {
    listen 80;
    server_name _;
    
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;
    
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_cache_bypass \$http_upgrade;
    }
    
    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }
    
    location / {
        root $DASHBOARD_PATH/dist;
        index index.html;
        try_files \$uri \$uri/ /index.html;
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)\$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    location /health {
        access_log off;
        return 200 "OK";
        add_header Content-Type text/plain;
    }
}
EOF
    
    ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t
    log_success "Nginx configured"
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > "$SYSTEMD_SERVICE" << EOF
[Unit]
Description=Packet Inspection Transformer - Malware Detection API
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_PATH/bin"
ExecStart=$VENV_PATH/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

StandardOutput=append:$LOG_DIR/uvicorn.log
StandardError=append:$LOG_DIR/uvicorn.error.log

NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $PROJECT_DIR/model

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable packet-inspection-transformer
    log_success "Systemd service created"
}

# ============================================================================
# Service Control Functions
# ============================================================================
start_backend() {
    log_info "Starting FastAPI backend..."
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        log_error "Virtual environment not found. Run setup first!"
        exit 1
    fi
    
    # Check if uvicorn exists
    if [ ! -f "$VENV_PATH/bin/uvicorn" ]; then
        log_error "uvicorn not found. Run setup first!"
        exit 1
    fi
    
    # Kill existing processes
    stop_services
    
    # Create start script with proper background execution
    cat > /tmp/start_uvicorn.sh << 'SCRIPT'
#!/bin/bash
trap '' HUP INT QUIT TSTP
cd /opt/packet-inspection-transformer
exec /opt/packet-inspection-transformer/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 >> /opt/packet-inspection-transformer/logs/uvicorn.log 2>&1 &
SCRIPT
    
    chmod +x /tmp/start_uvicorn.sh
    
    # Start in background with proper detachment
    cd /
    nohup /tmp/start_uvicorn.sh > /dev/null 2>&1 &
    Uvicorn_PID=$!
    
    sleep 3
    
    if kill -0 "$Uvicorn_PID" 2>/dev/null; then
        disown "$Uvicorn_PID"
        echo "$Uvicorn_PID" > "$PID_FILE"
        log_success "Backend started (PID: $Uvicorn_PID)"
    else
        log_error "Backend failed to start"
        exit 1
    fi
}

start_nginx() {
    log_info "Starting/restarting Nginx..."
    systemctl restart nginx
    if systemctl is-active --quiet nginx; then
        log_success "Nginx is running"
    else
        log_error "Nginx failed to start"
        exit 1
    fi
}

start_services() {
    log_info "Starting all services..."
    mkdir -p "$LOG_DIR"
    start_backend
    start_nginx
    log_success "All services started"
}

# ============================================================================
# Main Operations
# ============================================================================
do_setup() {
    echo "=============================================="
    echo "  Packet Inspection Transformer - Setup"
    echo "=============================================="
    echo ""
    
    check_root
    update_system
    clean_all
    install_python
    install_nodejs
    install_nginx
    install_certbot
    create_directories
    setup_venv
    build_frontend
    create_nginx_config
    create_systemd_service
    
    log_success "Setup completed!"
    echo ""
    echo "Next: Run 'sudo ./deploy.sh run' to start services"
}

do_run() {
    echo "=============================================="
    echo "  Packet Inspection Transformer - Start"
    echo "=============================================="
    echo ""
    
    check_root
    start_services
    
    echo ""
    echo "=============================================="
    echo "  Services started successfully!"
    echo "=============================================="
    echo ""
    echo "Dashboard: http://$(get_server_ip)"
    echo "API: http://$(get_server_ip)/api"
    echo ""
}

do_restart() {
    echo "=============================================="
    echo "  Packet Inspection Transformer - Restart"
    echo "=============================================="
    echo ""
    
    check_root
    stop_services
    sleep 2
    start_services
    
    log_success "All services restarted!"
}

do_stop() {
    echo "=============================================="
    echo "  Packet Inspection Transformer - Stop"
    echo "=============================================="
    echo ""
    
    check_root
    stop_services
    log_success "All services stopped"
}

do_clean() {
    echo "=============================================="
    echo "  Packet Inspection Transformer - Clean"
    echo "=============================================="
    echo ""
    
    check_root
    clean_all
    log_success "System cleaned"
}

do_status() {
    echo "=============================================="
    echo "  Service Status"
    echo "=============================================="
    echo ""
    
    # Check nginx
    if systemctl is-active --quiet nginx; then
        echo -e "${GREEN}✓ Nginx${NC} - Running"
    else
        echo -e "${RED}✗ Nginx${NC} - Not running"
    fi
    
    # Check backend
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${GREEN}✓ Backend (PID: $PID)${NC} - Running"
        else
            echo -e "${RED}✗ Backend${NC} - Not running"
        fi
    else
        echo -e "${RED}✗ Backend${NC} - Not running"
    fi
    
    echo ""
}

show_help() {
    echo "Packet Inspection Transformer - Deployment Script"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  setup    - Full installation (cleans existing, installs all)"
    echo "  run      - Start all services"
    echo "  restart  - Restart all services"
    echo "  stop     - Stop all services"
    echo "  clean    - Remove all installations"
    echo "  status   - Show service status"
    echo "  help     - Show this help message"
    echo ""
}

# ============================================================================
# Main Entry Point
# ============================================================================
main() {
    local command="${1:-help}"
    
    case "$command" in
        setup)   do_setup ;;
        run)     do_run ;;
        restart) do_restart ;;
        stop)    do_stop ;;
        clean)   do_clean ;;
        status)  do_status ;;
        help|--help|-h) show_help ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"