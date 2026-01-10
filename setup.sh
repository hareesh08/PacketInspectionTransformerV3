#!/bin/bash

# =============================================================================
# Packet Inspection Transformer - Automated Deployment Script
# =============================================================================
# Fully automatic deployment for production environments
# Supports access via https://<vmip> with self-signed SSL certificates
# Includes automatic Docker installation if not present
# Supports HTTP-only mode for IP-based deployments (no SSL)
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_VERSION="1.1.0"
PROJECT_NAME="Packet Inspection Transformer"
CONTAINER_PREFIX="pit"
VM_IP=""
DEPLOYMENT_MODE="auto"  # auto, http, https

# Functions
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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_warning "Not running as root. Some operations may require sudo."
        SUDO="sudo"
    else
        SUDO=""
    fi
}

# Detect VM IP address
detect_vm_ip() {
    log_info "Detecting VM IP address..."
    
    # Try multiple methods to detect IP
    if command -v ip &> /dev/null; then
        VM_IP=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K[0-9.]+' | head -1)
    fi
    
    if [[ -z "$VM_IP" ]]; then
        VM_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi
    
    if [[ -z "$VM_IP" ]]; then
        VM_IP=$(curl -s ifconfig.me 2>/dev/null || echo "")
    fi
    
    if [[ -z "$VM_IP" ]]; then
        VM_IP="localhost"
        log_warning "Could not detect VM IP. Using 'localhost'"
    fi
    
    log_success "Detected VM IP: $VM_IP"
}

# Check and install Docker
install_docker() {
    log_info "Installing Docker..."
    
    if command -v docker &> /dev/null; then
        log_success "Docker is already installed"
        return 0
    fi
    
    # Check OS
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
    else
        OS="unknown"
    fi
    
    # Install Docker based on OS
    if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
        log_info "Installing Docker on Ubuntu/Debian..."
        
        # Update package index
        $SUDO apt-get update -qq
        
        # Install dependencies
        $SUDO apt-get install -y -qq apt-transport-https ca-certificates curl gnupg lsb-release
        
        # Add Docker's official GPG key
        $SUDO install -m 0755 -d /etc/apt/keyrings
        curl -fsSL "https://download.docker.com/linux/${OS}/gpg" | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        $SUDO chmod a+r /etc/apt/keyrings/docker.gpg
        
        # Add Docker repository
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${OS} ${VERSION_CODENAME} stable" | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Install Docker
        $SUDO apt-get update -qq
        $SUDO apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
        
    elif [[ "$OS" == "centos" || "$OS" == "rhel" || "$OS" == "fedora" ]]; then
        log_info "Installing Docker on CentOS/RHEL/Fedora..."
        
        # Install dependencies
        $SUDO yum install -y -q yum-utils
        
        # Add Docker repository
        $SUDO yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        
        # Install Docker
        $SUDO yum install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
        
        # Start Docker
        $SUDO systemctl start docker
        $SUDO systemctl enable docker
        
    else
        log_error "Unsupported OS: $OS"
        log_info "Please install Docker manually and run this script again."
        exit 1
    fi
    
    # Add current user to docker group
    if ! groups | grep -q docker; then
        $SUDO usermod -aG docker $USER
        log_info "Added current user to docker group (may require logout/login)"
    fi
    
    # Wait for Docker to be ready
    sleep 3
    
    log_success "Docker installed successfully"
}

# Check and install Docker Compose
install_docker_compose() {
    log_info "Checking Docker Compose..."
    
    # Check if docker compose plugin is available (new Docker installations)
    if docker compose version &>/dev/null; then
        log_success "Docker Compose (plugin) is installed: $(docker compose version)"
        return 0
    fi
    
    # Check if standalone docker-compose is available
    if command -v docker-compose &> /dev/null; then
        log_success "Docker Compose (standalone) is installed: $(docker-compose --version)"
        return 0
    fi
    
    log_info "Installing Docker Compose..."
    
    # Install Docker Compose (standalone)
    local compose_version="v2.24.5"
    $SUDO curl -fsSL "https://github.com/docker/compose/releases/download/${compose_version}/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose
    $SUDO chmod +x /usr/local/bin/docker-compose
    
    # Create symlink for docker-compose
    $SUDO ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose 2>/dev/null || true
    
    log_success "Docker Compose installed successfully"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_warning "Docker is not installed"
        if [[ "$AUTO_INSTALL" == "true" ]]; then
            install_docker
        else
            missing_deps+=("docker")
        fi
    else
        log_success "Docker is installed: $(docker --version)"
    fi
    
    # Check Docker Compose
    if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
        log_warning "Docker Compose is not installed"
        if [[ "$AUTO_INSTALL" == "true" ]]; then
            install_docker_compose
        else
            missing_deps+=("docker-compose")
        fi
    else
        local compose_version=$(docker compose version 2>/dev/null || docker-compose --version 2>/dev/null)
        log_success "Docker Compose is installed: $compose_version"
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        log_warning "Git is not installed"
        if [[ "$AUTO_INSTALL" == "true" ]]; then
            log_info "Installing git..."
            $SUDO apt-get update -qq && $SUDO apt-get install -y -qq git 2>/dev/null || \
            $SUDO yum install -y -q git 2>/dev/null || true
        fi
    else
        log_success "Git is installed: $(git --version)"
    fi
    
    # Check OpenSSL
    if ! command -v openssl &> /dev/null; then
        log_error "OpenSSL is not installed"
        missing_deps+=("openssl")
    else
        log_success "OpenSSL is installed: $(openssl version)"
    fi
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        log_warning "curl is not installed"
        if [[ "$AUTO_INSTALL" == "true" ]]; then
            log_info "Installing curl..."
            $SUDO apt-get update -qq && $SUDO apt-get install -y -qq curl 2>/dev/null || \
            $SUDO yum install -y -q curl 2>/dev/null || true
        fi
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Please install the missing dependencies and run this script again."
        exit 1
    fi
    
    # Check Docker daemon
    local docker_check=0
    for i in {1..10}; do
        if docker info &> /dev/null; then
            docker_check=1
            break
        fi
        log_info "Waiting for Docker daemon... (attempt $i/10)"
        sleep 2
    done
    
    if [[ $docker_check -eq 0 ]]; then
        log_error "Docker daemon is not running or you don't have permission to access it."
        log_info "Attempting to start Docker..."
        $SUDO systemctl start docker 2>/dev/null || $SUDO service docker start 2>/dev/null || true
        sleep 3
        
        if ! docker info &> /dev/null; then
            log_error "Could not start Docker daemon."
            log_info "Please start Docker manually:"
            log_info "  sudo systemctl start docker"
            exit 1
        fi
    fi
    
    log_success "All prerequisites are met"
}

# Stop existing containers
stop_existing_containers() {
    log_info "Stopping existing containers..."
    
    # Stop containers if they exist
    docker compose down 2>/dev/null || true
    
    # Remove any orphaned containers
    for container in $(docker ps -aq --filter "name=${CONTAINER_PREFIX}-" 2>/dev/null); do
        log_info "Removing container: $container"
        docker rm -f "$container" 2>/dev/null || true
    done
    
    log_success "Existing containers cleaned up"
}

# Create required directories
create_directories() {
    log_info "Creating required directories..."
    
    mkdir -p nginx/certificates
    mkdir -p nginx/html
    mkdir -p logs
    mkdir -p data
    mkdir -p model
    mkdir -p config
    
    log_success "Directories created"
}

# Generate SSL certificates
generate_ssl_certificates() {
    log_info "Generating SSL certificates for IP: $VM_IP"
    
    local cert_dir="nginx/certificates"
    local cert_file="${cert_dir}/fullchain.pem"
    local key_file="${cert_dir}/privkey.pem"
    
    # Create directories for certificates
    mkdir -p "${cert_dir}/live/${VM_IP}"
    mkdir -p "${cert_dir}/archive"
    
    # Generate self-signed certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "${key_file}" \
        -out "${cert_file}" \
        -subj "/C=US/ST=State/L=City/O=${PROJECT_NAME}/CN=${VM_IP}" \
        -addext "subjectAltName=IP:${VM_IP},DNS:${VM_IP}" \
        2>/dev/null
    
    # Also create symlinks for Let's Encrypt style paths
    mkdir -p "${cert_dir}/live/${VM_IP}"
    ln -sf "${cert_file}" "${cert_dir}/live/${VM_IP}/fullchain.pem" 2>/dev/null || true
    ln -sf "${key_file}" "${cert_dir}/live/${VM_IP}/privkey.pem" 2>/dev/null || true
    ln -sf "${cert_file}" "${cert_dir}/live/${VM_IP}/chain.pem" 2>/dev/null || true
    
    # Set permissions
    chmod 600 "${key_file}"
    chmod 644 "${cert_file}"
    
    log_success "SSL certificates generated"
    log_info "Certificate location: ${cert_dir}/"
}

# Update nginx configuration for IP-based access (HTTPS mode)
update_nginx_config() {
    log_info "Updating Nginx configuration for IP-based access..."
    
    local conf_file="nginx/conf.d/default.conf"
    
    # Replace ${DOMAIN:-localhost} with VM_IP in the nginx config
    if [[ -f "$conf_file" ]]; then
        sed -i "s/\${DOMAIN:-localhost}/${VM_IP}/g" "$conf_file"
        log_success "Nginx configuration updated (HTTPS mode)"
    else
        log_error "Nginx configuration file not found: $conf_file"
        exit 1
    fi
}

# Restore nginx configuration to template
restore_nginx_config() {
    log_info "Restoring Nginx configuration to template..."
    
    local conf_file="nginx/conf.d/default.conf"
    local template_file="nginx/conf.d/default.conf.template"
    
    # If template exists, restore from it
    if [[ -f "$template_file" ]]; then
        cp "$template_file" "$conf_file"
        log_success "Nginx configuration restored from template"
    else
        # Otherwise, just revert the domain substitution
        if [[ -f "$conf_file" ]]; then
            sed -i "s/${VM_IP}/\${DOMAIN:-localhost}/g" "$conf_file"
            log_success "Nginx configuration reverted"
        fi
    fi
}

# Switch to HTTP-only mode (no SSL)
switch_to_http_mode() {
    log_info "Switching to HTTP-only mode..."
    
    local http_conf="nginx-http.conf"
    local target_conf="nginx/conf.d/default.conf"
    
    # Backup current config if it exists
    if [[ -f "$target_conf" ]]; then
        cp "$target_conf" "${target_conf}.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
    fi
    
    # Copy HTTP-only config
    if [[ -f "$http_conf" ]]; then
        cp "$http_conf" "$target_conf"
        log_success "Switched to HTTP-only mode"
    else
        log_error "HTTP configuration file not found: $http_conf"
        exit 1
    fi
    
    DEPLOYMENT_MODE="http"
}

# Switch to HTTPS mode (with SSL)
switch_to_https_mode() {
    log_info "Switching to HTTPS mode..."
    
    local target_conf="nginx/conf.d/default.conf"
    
    # Restore from backup if available
    local latest_backup=$(ls -t "${target_conf}.bak."* 2>/dev/null | head -1)
    if [[ -n "$latest_backup" ]]; then
        cp "$latest_backup" "$target_conf"
        log_success "Restored HTTPS configuration from backup"
    else
        # Regenerate config
        restore_nginx_config
    fi
    
    # Regenerate SSL certificates
    generate_ssl_certificates
    
    DEPLOYMENT_MODE="https"
}

# Create environment file
create_env_file() {
    log_info "Creating environment configuration..."
    
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.example" ]]; then
            cp ".env.example" ".env"
        fi
    fi
    
    # Update .env with VM_IP
    if [[ -f ".env" ]]; then
        # Update DOMAIN to use VM_IP
        sed -i "s/^DOMAIN=.*/DOMAIN=${VM_IP}/g" ".env"
        
        # Update VITE_API_URL
        sed -i "s|^VITE_API_URL=.*|VITE_API_URL=https://${VM_IP}|g" ".env"
        
        # Update LETSENCRYPT_EMAIL (use a placeholder for self-signed)
        sed -i "s|^LETSENCRYPT_EMAIL=.*|LETSENCRYPT_EMAIL=admin@${VM_IP}|g" ".env"
        
        log_success "Environment file updated"
    fi
}

# Fix Dockerfiles if needed
fix_dockerfiles() {
    log_info "Checking and fixing Dockerfiles..."
    
    # Fix Frontend/Dockerfile - handle npm install and apt-get/apk
    if [[ -f "Frontend/Dockerfile" ]]; then
        # Fix apt-get to apk for Alpine nginx base image
        if grep -q "apt-get update && apt-get install" "Frontend/Dockerfile"; then
            log_info "Fixing Frontend/Dockerfile (apt-get -> apk)"
            sed -i 's/apt-get update && apt-get install -y --no-install-recommends.*curl.*ca-certificates.*&& rm -rf \/var\/lib\/apt\/lists\*/apk add --no-cache curl ca-certificates/g' "Frontend/Dockerfile"
        fi
        
        # Ensure npm ci is replaced with conditional install (handles missing lock file)
        if grep -q "RUN npm ci --quiet --no-audit" "Frontend/Dockerfile"; then
            log_info "Fixing Frontend/Dockerfile (npm ci -> npm install fallback)"
            # Replace the problematic npm ci line with npm install
            sed -i 's/RUN npm ci --quiet --no-audit/RUN npm install --no-audit/g' "Frontend/Dockerfile"
            log_success "Fixed npm ci -> npm install"
        else
            log_success "Frontend/Dockerfile npm install is already fixed"
        fi
    fi
    
    # Ensure main Dockerfile has curl (Debian-based, uses apt-get)
    if [[ -f "Dockerfile" ]]; then
        log_info "Dockerfile looks good (Debian-based)"
    fi
}

# Build and start containers
deploy_containers() {
    log_info "Building and starting containers..."
    
    # Set environment variables for build
    export DOMAIN="${VM_IP}"
    
    # Fix Dockerfiles if needed
    fix_dockerfiles
    
    # Build the images (no cache to ensure latest changes)
    log_info "Building Docker images (this may take a few minutes)..."
    log_info "Cleaning Docker build cache..."
    docker builder prune -af 2>/dev/null || true
    docker compose build --no-cache --pull
    
    # Start the services
    log_info "Starting services..."
    docker compose up -d
    
    log_success "Containers deployed"
}

# Quick rebuild (rebuild frontend only, restart containers)
quick_rebuild() {
    log_info "Performing quick rebuild (frontend only)..."
    
    # Rebuild frontend without full cache clean
    log_info "Building frontend image..."
    docker compose build frontend --no-cache
    
    # Restart containers
    log_info "Restarting containers..."
    docker compose up -d frontend
    
    log_success "Quick rebuild complete"
}

# Quick restart (no rebuild)
quick_restart() {
    log_info "Performing quick restart (no rebuild)..."
    
    docker compose restart
    
    log_success "Quick restart complete"
}

# Check SSL certificates and fallback to HTTP if missing
ensure_ssl_or_fallback() {
    local cert_dir="nginx/certificates/live/${VM_IP}"
    local cert_file="${cert_dir}/fullchain.pem"
    local key_file="${cert_dir}/privkey.pem"
    
    if [[ ! -f "$cert_file" || ! -f "$key_file" ]]; then
        log_warning "SSL certificates not found. Falling back to HTTP mode..."
        switch_to_http_mode
        return 1  # Indicates fallback happened
    fi
    
    return 0  # SSL is available
}

# Wait for services to be healthy
wait_for_services() {
    log_info "Waiting for services to be healthy..."
    
    local max_attempts=60
    local attempt=0
    local backend_healthy=false
    local frontend_healthy=false
    
    while [[ $attempt -lt $max_attempts ]]; do
        attempt=$((attempt + 1))
        
        # Check backend health
        if ! $backend_healthy; then
            if curl -sf http://localhost:8000/health &>/dev/null; then
                log_success "Backend is healthy"
                backend_healthy=true
            fi
        fi
        
        # Check frontend health (basic nginx check)
        if ! $frontend_healthy; then
            if curl -sf http://localhost:80/health &>/dev/null || curl -sf http://localhost/ &>/dev/null; then
                log_success "Frontend is healthy"
                frontend_healthy=true
            fi
        fi
        
        if $backend_healthy && $frontend_healthy; then
            break
        fi
        
        log_info "Waiting for services... (attempt $attempt/$max_attempts)"
        sleep 2
    done
    
    if ! $backend_healthy; then
        log_warning "Backend may not be fully healthy yet"
    fi
    
    if ! $frontend_healthy; then
        log_warning "Frontend may not be fully healthy yet"
    fi
    
    log_success "Service health check completed"
}

# Configure firewall
configure_firewall() {
    log_info "Configuring firewall..."
    
    # Check if ufw is available
    if command -v ufw &> /dev/null; then
        log_info "Configuring UFW firewall..."
        $SUDO ufw allow 80/tcp comment 'HTTP' 2>/dev/null || true
        $SUDO ufw allow 443/tcp comment 'HTTPS' 2>/dev/null || true
        $SUDO ufw allow 22/tcp comment 'SSH' 2>/dev/null || true
        
        # Enable UFW if not already enabled
        if ! $SUDO ufw status | grep -q "Status: active"; then
            log_warning "UFW is not active. Enabling..."
            echo "y" | $SUDO ufw enable 2>/dev/null || true
        fi
        
        log_success "UFW configured"
    elif command -v firewall-cmd &> /dev/null; then
        log_info "Configuring firewalld..."
        $SUDO firewall-cmd --permanent --add-service=http 2>/dev/null || true
        $SUDO firewall-cmd --permanent --add-service=https 2>/dev/null || true
        $SUDO firewall-cmd --reload 2>/dev/null || true
        log_success "firewalld configured"
    elif command -v iptables &> /dev/null; then
        log_info "Configuring iptables..."
        $SUDO iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || \
            $SUDO iptables -I INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
        $SUDO iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || \
            $SUDO iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || true
        log_success "iptables configured"
    else
        log_warning "No supported firewall found. Please configure firewall manually."
    fi
}

# Print deployment summary
print_summary() {
    local mode_text=""
    if [[ "$DEPLOYMENT_MODE" == "http" ]]; then
        mode_text="HTTP (No SSL)"
    else
        mode_text="HTTPS (Self-signed SSL)"
    fi
    
    echo ""
    echo "============================================================================="
    echo "                    ${GREEN}DEPLOYMENT COMPLETE${NC}"
    echo "============================================================================="
    echo ""
    echo -e "${BLUE}Deployment Mode:${NC} ${CYAN}${mode_text}${NC}"
    echo ""
    
    if [[ "$DEPLOYMENT_MODE" == "http" ]]; then
        echo -e "${BLUE}Access your application:${NC}"
        echo ""
        echo "  HTTP:   ${GREEN}http://${VM_IP}${NC}"
        echo ""
        echo -e "${BLUE}Service Endpoints:${NC}"
        echo ""
        echo "  Frontend:  http://localhost:80"
        echo "  Backend:   http://localhost:8000"
        echo "  Health:    http://${VM_IP}/health"
        echo "  API:       http://${VM_IP}/api/"
    else
        echo -e "${BLUE}Access your application:${NC}"
        echo ""
        echo "  HTTPS:  ${GREEN}https://${VM_IP}${NC}"
        echo ""
        echo -e "${BLUE}Service Endpoints:${NC}"
        echo ""
        echo "  Frontend:  http://localhost:80 (HTTP redirect to HTTPS)"
        echo "  Backend:   http://localhost:8000"
        echo "  Health:    https://${VM_IP}/health"
        echo "  API:       https://${VM_IP}/api/"
    fi
    
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo ""
    echo "  Full deploy:  ./setup.sh"
    echo "  Quick rebuild: ./setup.sh --quick-rebuild"
    echo "  Quick restart: ./setup.sh --quick-restart"
    echo "  Switch to HTTP:  ./setup.sh --http"
    echo "  Switch to HTTPS: ./setup.sh --https"
    echo "  View logs:    docker compose logs -f"
    echo "  Stop:         docker compose down"
    echo "  Restart:      docker compose restart"
    echo "  Status:       docker compose ps"
    echo ""
    
    if [[ "$DEPLOYMENT_MODE" == "http" ]]; then
        echo -e "${YELLOW}Note:${NC}"
        echo ""
        echo "  - Running in HTTP-only mode (no SSL)"
        echo "  - Suitable for development and testing"
        echo "  - For production, use HTTPS mode or acquire a domain"
        echo "  - Run './setup.sh --https' to enable HTTPS"
    else
        echo -e "${BLUE}Note:${NC}"
        echo ""
        echo "  - Self-signed SSL certificate has been generated"
        echo "  - Accept the certificate warning in your browser"
        echo "  - For production, consider using Let's Encrypt with a domain"
        echo "  - Run './setup.sh --http' to switch to HTTP-only mode"
    fi
    
    echo ""
    echo "============================================================================="
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    local all_healthy=true
    
    # Check if containers are running
    local running_containers=$(docker ps --filter "name=${CONTAINER_PREFIX}-" -q | wc -l)
    log_info "Running containers: $running_containers"
    
    if [[ "$running_containers" -lt 2 ]]; then
        log_warning "Expected at least 2 containers (frontend, backend)"
        all_healthy=false
    fi
    
    # Test HTTPS endpoint
    if command -v curl &> /dev/null; then
        local https_response=$(curl -sfk https://${VM_IP}/health 2>&1 || echo "FAILED")
        if [[ "$https_response" != "FAILED" ]]; then
            log_success "HTTPS endpoint is responding"
            echo "Response: $https_response"
        else
            log_warning "HTTPS endpoint may not be responding yet"
            all_healthy=false
        fi
    fi
    
    if $all_healthy; then
        log_success "Deployment verified successfully"
        return 0
    else
        log_warning "Some services may need more time to start"
        return 1
    fi
}

# Display help
show_help() {
    echo ""
    echo "============================================================================="
    echo "      ${GREEN}${PROJECT_NAME} - Deployment Script${NC}"
    echo "                      Version: ${SCRIPT_VERSION}"
    echo "============================================================================="
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -a, --auto              Automatic deployment (default)"
    echo "  --http                  Deploy in HTTP-only mode (no SSL)"
    echo "  --https                 Deploy in HTTPS mode (with SSL)"
    echo "  --quick-rebuild         Quick rebuild (frontend only, no cache clean)"
    echo "  --quick-restart         Quick restart (no rebuild)"
    echo "  --switch-http           Switch to HTTP mode (after deployment)"
    echo "  --switch-https          Switch to HTTPS mode (after deployment)"
    echo "  --status                Show container status"
    echo "  --logs                  Show container logs"
    echo "  --stop                  Stop all containers"
    echo ""
    echo "Examples:"
    echo "  $0                      # Automatic deployment with SSL"
    echo "  $0 --http               # Deploy without SSL (HTTP only)"
    echo "  $0 --quick-rebuild      # Quick rebuild after code changes"
    echo "  $0 --switch-http        # Switch running deployment to HTTP mode"
    echo ""
    echo "============================================================================="
}

# Show container status
show_status() {
    echo ""
    echo "============================================================================="
    echo "                    ${GREEN}Container Status${NC}"
    echo "============================================================================="
    echo ""
    docker compose ps
    echo ""
}

# Show container logs
show_logs() {
    echo ""
    echo "============================================================================="
    echo "                    ${GREEN}Container Logs${NC}"
    echo "============================================================================="
    echo ""
    docker compose logs -f
}

# Stop all containers
stop_containers() {
    log_info "Stopping all containers..."
    docker compose down
    log_success "All containers stopped"
}

# Full deployment with automatic fallback
full_deploy() {
    echo ""
    echo "============================================================================="
    echo "      ${GREEN}${PROJECT_NAME} - Automated Deployment Script${NC}"
    echo "                      Version: ${SCRIPT_VERSION}"
    echo "============================================================================="
    echo ""
    
    # Enable auto-install by default for fully automatic deployment
    AUTO_INSTALL="true"
    
    check_root
    detect_vm_ip
    check_prerequisites
    stop_existing_containers
    create_directories
    
    # Try HTTPS first, fallback to HTTP if SSL fails
    if [[ "$DEPLOYMENT_MODE" == "auto" ]]; then
        log_info "Attempting HTTPS deployment..."
        if generate_ssl_certificates 2>/dev/null; then
            update_nginx_config
            DEPLOYMENT_MODE="https"
        else
            log_warning "SSL certificate generation failed, falling back to HTTP..."
            switch_to_http_mode
        fi
    elif [[ "$DEPLOYMENT_MODE" == "https" ]]; then
        generate_ssl_certificates
        update_nginx_config
    else
        switch_to_http_mode
    fi
    
    create_env_file
    fix_dockerfiles
    deploy_containers
    wait_for_services
    configure_firewall
    
    echo ""
    verify_deployment
    print_summary
}

# Handle command line arguments
handle_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -a|--auto)
                DEPLOYMENT_MODE="auto"
                shift
                ;;
            --http)
                DEPLOYMENT_MODE="http"
                shift
                ;;
            --https)
                DEPLOYMENT_MODE="https"
                shift
                ;;
            --quick-rebuild)
                detect_vm_ip
                quick_rebuild
                exit 0
                ;;
            --quick-restart)
                quick_restart
                exit 0
                ;;
            --switch-http)
                detect_vm_ip
                switch_to_http_mode
                docker compose up -d
                log_success "Switched to HTTP mode"
                exit 0
                ;;
            --switch-https)
                detect_vm_ip
                switch_to_https_mode
                docker compose up -d
                log_success "Switched to HTTPS mode"
                exit 0
                ;;
            --status)
                show_status
                exit 0
                ;;
            --logs)
                show_logs
                exit 0
                ;;
            --stop)
                stop_containers
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Main execution
main() {
    handle_args "$@"
    full_deploy
}

# Run main function
main "$@"