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
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="/tmp/uvicorn.pid"

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_warn "Not running as root - some operations may require sudo"
    fi
}

# Create logs directory
setup_logs() {
    mkdir -p "$LOG_DIR"
    log_info "Logs directory: $LOG_DIR"
}

# Kill existing uvicorn process
kill_uvicorn() {
    log_info "Stopping existing uvicorn processes..."
    
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
    
    # Wait for processes to terminate
    sleep 2
    
    log_success "All uvicorn processes stopped"
}

# Start uvicorn
start_uvicorn() {
    log_info "Starting FastAPI backend with uvicorn..."
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        log_error "Virtual environment not found. Run setup.sh first!"
        exit 1
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Check if port 8000 is already in use
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warn "Port 8000 is already in use. Attempting to free it..."
        fuser -k 8000/tcp 2>/dev/null || true
        sleep 2
    fi
    
    # Create nohup script
    cat > /tmp/start_uvicorn.sh << 'SCRIPT'
#!/bin/bash
cd /opt/packet-inspection-transformer
source /opt/packet-inspection-transformer/venv/bin/activate
exec uvicorn app:app --host 0.0.0.0 --port 8000 >> /opt/packet-inspection-transformer/logs/uvicorn.log 2>&1
SCRIPT
    
    chmod +x /tmp/start_uvicorn.sh
    
    # Start in background
    nohup /tmp/start_uvicorn.sh &
    Uvicorn_PID=$!
    
    echo "$Uvicorn_PID" > "$PID_FILE"
    
    log_success "Uvicorn started (PID: $Uvicorn_PID)"
    
    # Wait a bit and check if process is running
    sleep 3
    
    if kill -0 "$Uvicorn_PID" 2>/dev/null; then
        log_success "Backend is running successfully"
    else
        log_error "Backend failed to start. Check logs at $LOG_DIR/uvicorn.log"
        exit 1
    fi
}

# Start nginx
start_nginx() {
    log_info "Starting nginx..."
    
    if systemctl is-active --quiet nginx; then
        log_info "Nginx is already running, restarting..."
        systemctl restart nginx
    else
        systemctl start nginx
    fi
    
    if systemctl is-active --quiet nginx; then
        log_success "Nginx is running"
    else
        log_error "Nginx failed to start"
        exit 1
    fi
}

# Check services status
check_status() {
    echo ""
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
    
    # Check uvicorn
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            echo -e "${GREEN}✓ Uvicorn (PID: $PID)${NC} - Running"
        else
            echo -e "${RED}✗ Uvicorn${NC} - Not running (stale PID file)"
        fi
    else
        echo -e "${RED}✗ Uvicorn${NC} - Not running"
    fi
    
    echo ""
}

# Main function
main() {
    echo "=============================================="
    echo "  Packet Inspection Transformer - Run"
    echo "=============================================="
    echo ""
    
    check_root
    setup_logs
    kill_uvicorn
    start_uvicorn
    start_nginx
    check_status
    
    echo ""
    echo "=============================================="
    log_success "All services started successfully!"
    echo "=============================================="
    echo ""
    echo "Access your dashboard at:"
    echo "  http://<VM_PUBLIC_IP>"
    echo ""
    echo "API endpoint:"
    echo "  http://<VM_PUBLIC_IP>/api"
    echo ""
    echo "Logs:"
    echo "  $LOG_DIR/uvicorn.log"
    echo ""
}

# Run main function
main "$@"