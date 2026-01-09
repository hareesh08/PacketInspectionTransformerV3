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

# Kill uvicorn process
kill_uvicorn() {
    log_info "Stopping uvicorn backend..."
    
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
    
    # Force kill if still running
    fuser -k 8000/tcp 2>/dev/null || true
    
    log_success "Uvicorn stopped"
}

# Start uvicorn
start_uvicorn() {
    log_info "Starting uvicorn backend..."
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        log_error "Virtual environment not found. Run setup.sh first!"
        exit 1
    fi
    
    # Check if uvicorn is available
    UVICORN_PATH="$VENV_PATH/bin/uvicorn"
    if [ ! -f "$UVICORN_PATH" ]; then
        log_error "uvicorn not found in virtual environment. Run setup.sh to install dependencies!"
        exit 1
    fi
    
    # Create start script with proper background execution
    cat > /tmp/start_uvicorn.sh << SCRIPT
#!/bin/bash
# Ensure process survives SSH disconnect
trap '' HUP INT QUIT TSTP

cd /opt/packet-inspection-transformer

# Use full path to uvicorn
exec /opt/packet-inspection-transformer/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 >> /opt/packet-inspection-transformer/logs/uvicorn.log 2>&1 &
SCRIPT
    
    chmod +x /tmp/start_uvicorn.sh
    
    # Start in background with nohup, redirect output, and detach from terminal
    cd /
    nohup /tmp/start_uvicorn.sh > /dev/null 2>&1 &
    Uvicorn_PID=$!
    
    # Wait for startup
    sleep 2
    
    # Verify process is running and not in a stopped state
    if kill -0 "$Uvicorn_PID" 2>/dev/null; then
        # Disown the process to fully detach from shell
        disown "$Uvicorn_PID"
        echo "$Uvicorn_PID" > "$PID_FILE"
        log_success "Uvicorn started (PID: $Uvicorn_PID)"
        
        # Wait a bit and verify it's still running
        sleep 3
        if kill -0 "$Uvicorn_PID" 2>/dev/null; then
            log_success "Backend is running successfully (survives SSH disconnect)"
        else
            log_error "Backend failed to start. Check logs at $LOG_DIR/uvicorn.log"
            tail -50 "$LOG_DIR/uvicorn.log" 2>/dev/null || true
            exit 1
        fi
    else
        log_error "Backend failed to start. Check logs at $LOG_DIR/uvicorn.log"
        tail -50 "$LOG_DIR/uvicorn.log" 2>/dev/null || true
        exit 1
    fi
}

# Restart nginx
restart_nginx() {
    log_info "Restarting nginx..."
    
    if systemctl is-active --quiet nginx; then
        systemctl restart nginx
        log_success "Nginx restarted"
    else
        systemctl start nginx
        log_success "Nginx started"
    fi
}

# Check services status
check_status() {
    echo ""
    echo "=============================================="
    echo "  Service Status After Restart"
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
    
    # Show recent logs
    echo ""
    echo "=============================================="
    echo "  Recent Backend Logs"
    echo "=============================================="
    tail -20 "$LOG_DIR/uvicorn.log" 2>/dev/null || echo "No logs available"
    
    echo ""
}

# Main function
main() {
    echo "=============================================="
    echo "  Packet Inspection Transformer - Restart"
    echo "=============================================="
    echo ""
    
    kill_uvicorn
    start_uvicorn
    restart_nginx
    check_status
    
    echo ""
    echo "=============================================="
    log_success "All services restarted successfully!"
    echo "=============================================="
    echo ""
    echo "Dashboard: http://<VM_PUBLIC_IP>"
    echo "API: http://<VM_PUBLIC_IP>/api"
    echo ""
}

# Run main function
main "$@"