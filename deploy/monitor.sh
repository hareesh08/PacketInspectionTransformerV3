#!/bin/bash

# =============================================================================
# Service Monitoring Script
# =============================================================================
# This script monitors the health of all services and can restart them if needed
# =============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000
MAX_RETRIES=3
RETRY_DELAY=5

# Check if a service is running on a specific port
check_port() {
    local port=$1
    local service_name=$2
    
    if lsof -i :$port > /dev/null 2>&1; then
        log_success "$service_name is running on port $port"
        return 0
    else
        log_error "$service_name is not running on port $port"
        return 1
    fi
}

# Check if a URL is responding
check_url() {
    local url=$1
    local service_name=$2
    local timeout=${3:-10}
    
    if curl -s --max-time $timeout "$url" > /dev/null; then
        log_success "$service_name is responding at $url"
        return 0
    else
        log_error "$service_name is not responding at $url"
        return 1
    fi
}

# Restart a PM2 process
restart_pm2_process() {
    local process_name=$1
    
    log_info "Restarting PM2 process: $process_name"
    pm2 restart $process_name
    sleep 3
    
    if pm2 list | grep -q "$process_name.*online"; then
        log_success "PM2 process $process_name restarted successfully"
        return 0
    else
        log_error "Failed to restart PM2 process $process_name"
        return 1
    fi
}

# Monitor backend service
monitor_backend() {
    log_info "Monitoring backend service..."
    
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if check_url "http://localhost:$BACKEND_PORT/health" "Backend"; then
            return 0
        fi
        
        retries=$((retries + 1))
        log_warning "Backend check failed (attempt $retries/$MAX_RETRIES)"
        
        if [ $retries -lt $MAX_RETRIES ]; then
            log_info "Attempting to restart backend..."
            restart_pm2_process "malware-backend"
            sleep $RETRY_DELAY
        fi
    done
    
    log_error "Backend service failed after $MAX_RETRIES attempts"
    return 1
}

# Monitor frontend service
monitor_frontend() {
    log_info "Monitoring frontend service..."
    
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if check_port $FRONTEND_PORT "Frontend"; then
            return 0
        fi
        
        retries=$((retries + 1))
        log_warning "Frontend check failed (attempt $retries/$MAX_RETRIES)"
        
        if [ $retries -lt $MAX_RETRIES ]; then
            log_info "Attempting to restart frontend..."
            restart_pm2_process "malware-frontend"
            sleep $RETRY_DELAY
        fi
    done
    
    log_error "Frontend service failed after $MAX_RETRIES attempts"
    return 1
}

# Monitor nginx service
monitor_nginx() {
    log_info "Monitoring nginx service..."
    
    if systemctl is-active --quiet nginx; then
        if check_url "http://localhost/" "Nginx"; then
            log_success "Nginx is running and responding"
            return 0
        else
            log_warning "Nginx is running but not responding, reloading..."
            systemctl reload nginx
            sleep 2
            
            if check_url "http://localhost/" "Nginx"; then
                log_success "Nginx reloaded successfully"
                return 0
            fi
        fi
    fi
    
    log_error "Nginx is not running, attempting to start..."
    systemctl start nginx
    sleep 3
    
    if systemctl is-active --quiet nginx; then
        log_success "Nginx started successfully"
        return 0
    else
        log_error "Failed to start nginx"
        return 1
    fi
}

# Check system resources
check_resources() {
    log_info "Checking system resources..."
    
    # Check memory usage
    local mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    log_info "Memory usage: ${mem_usage}%"
    
    if (( $(echo "$mem_usage > 90" | bc -l) )); then
        log_warning "High memory usage detected: ${mem_usage}%"
    fi
    
    # Check disk usage
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    log_info "Disk usage: ${disk_usage}%"
    
    if [ $disk_usage -gt 90 ]; then
        log_warning "High disk usage detected: ${disk_usage}%"
    fi
    
    # Check CPU load
    local cpu_load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    log_info "CPU load (1min): $cpu_load"
}

# Main monitoring function
run_monitor() {
    log_info "Starting service monitoring..."
    echo "=================================="
    
    local backend_ok=true
    local frontend_ok=true
    local nginx_ok=true
    
    # Monitor each service
    monitor_backend || backend_ok=false
    monitor_frontend || frontend_ok=false
    monitor_nginx || nginx_ok=false
    
    # Check system resources
    check_resources
    
    echo "=================================="
    
    # Summary
    if $backend_ok && $frontend_ok && $nginx_ok; then
        log_success "All services are healthy"
        return 0
    else
        log_error "Some services are unhealthy"
        
        # Send notification (if notification system is available)
        if command -v mail &> /dev/null; then
            echo "Service health check failed on $(hostname) at $(date)" | mail -s "Service Alert" root
        fi
        
        return 1
    fi
}

# Continuous monitoring mode
continuous_monitor() {
    local interval=${1:-300}  # Default 5 minutes
    
    log_info "Starting continuous monitoring (interval: ${interval}s)"
    
    while true; do
        run_monitor
        log_info "Next check in ${interval} seconds..."
        sleep $interval
    done
}

# Show service status
show_status() {
    echo "=== Service Status ==="
    echo
    
    echo "PM2 Processes:"
    pm2 list
    echo
    
    echo "Nginx Status:"
    systemctl status nginx --no-pager -l
    echo
    
    echo "Port Usage:"
    echo "Backend (port $BACKEND_PORT):"
    lsof -i :$BACKEND_PORT 2>/dev/null || echo "  No processes found"
    echo "Frontend (port $FRONTEND_PORT):"
    lsof -i :$FRONTEND_PORT 2>/dev/null || echo "  No processes found"
    echo "Nginx (port 80):"
    lsof -i :80 2>/dev/null || echo "  No processes found"
    echo
    
    echo "System Resources:"
    free -h
    df -h /
    uptime
}

# Main script logic
case "${1:-}" in
    "check")
        run_monitor
        ;;
    "continuous")
        continuous_monitor ${2:-300}
        ;;
    "status")
        show_status
        ;;
    *)
        echo "Usage: $0 {check|continuous|status}"
        echo
        echo "Commands:"
        echo "  check                 - Run a single health check"
        echo "  continuous [interval] - Run continuous monitoring (default: 300s)"
        echo "  status               - Show detailed service status"
        echo
        echo "Examples:"
        echo "  ./monitor.sh check              # Single check"
        echo "  ./monitor.sh continuous 60      # Monitor every minute"
        echo "  ./monitor.sh status             # Show status"
        exit 1
        ;;
esac