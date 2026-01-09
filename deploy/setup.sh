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

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root (use sudo)"
        exit 1
    fi
}

# Update system
update_system() {
    log_info "Updating system packages..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get upgrade -y -qq
    log_success "System updated"
}

# Install Python and dependencies
install_python() {
    log_info "Installing Python 3 and dependencies..."
    apt-get install -y -qq python3 python3-venv python3-pip curl wget git
    log_success "Python 3 installed"
}

# Install Node.js 20.x
install_nodejs() {
    log_info "Installing Node.js 20.x..."
    
    # Check if Node.js is already installed
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        log_warn "Node.js already installed: $NODE_VERSION"
    else
        # Install NodeSource repository
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -E -
        apt-get install -y -qq nodejs
        log_success "Node.js 20.x installed"
    fi
    
    # Verify installation
    node --version
    npm --version
}

# Install Nginx
install_nginx() {
    log_info "Installing Nginx..."
    apt-get install -y -qq nginx
    systemctl enable nginx
    systemctl start nginx
    log_success "Nginx installed and started"
}

# Install certbot for Let's Encrypt
install_certbot() {
    log_info "Installing certbot for Let's Encrypt SSL..."
    apt-get install -y -qq certbot python3-certbot-nginx
    log_success "Certbot installed"
}

# Auto-setup SSL with Let's Encrypt
auto_setup_ssl() {
    log_info "Checking for SSL configuration..."
    
    # Check if domain is provided via environment variable
    if [ -n "$DOMAIN" ]; then
        setup_ssl_with_domain "$DOMAIN"
        return
    fi
    
    # Try to detect domain from hostname or ask user
    DETECTED_DOMAIN=$(hostname -f 2>/dev/null | grep -P '^[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}' || echo "")
    
    if [ -n "$DETECTED_DOMAIN" ]; then
        log_info "Detected domain: $DETECTED_DOMAIN"
        read -p "Use this domain for SSL? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            setup_ssl_with_domain "$DETECTED_DOMAIN"
            return
        fi
    fi
    
    # Ask for domain
    echo ""
    log_info "For automatic SSL, enter your domain name"
    log_info "Leave blank to skip SSL setup (will use HTTP only)"
    read -p "Domain name (e.g., example.com): " DOMAIN
    
    if [ -n "$DOMAIN" ]; then
        setup_ssl_with_domain "$DOMAIN"
    else
        log_warn "Skipping SSL setup. Use HTTP only."
        log_info "To add SSL later, run: sudo ./setup-ssl.sh"
    fi
}

# Setup SSL with specific domain
setup_ssl_with_domain() {
    local DOMAIN="$1"
    log_info "Setting up SSL for domain: $DOMAIN"
    
    # Verify DNS resolution
    log_info "Verifying DNS for $DOMAIN..."
    RESOLVED_IP=$(dig +short "$DOMAIN" A @8.8.8.8 2>/dev/null | head -1 || echo "")
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    
    if [ -n "$RESOLVED_IP" ] && [ "$RESOLVED_IP" != "$SERVER_IP" ]; then
        log_warn "Domain DNS ($RESOLVED_IP) doesn't match server IP ($SERVER_IP)"
        log_warn "SSL certificate may not work. Ensure DNS is configured correctly."
        read -p "Continue anyway? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log_info "Skipping SSL setup"
            return
        fi
    fi
    
    # Create SSL nginx config
    log_info "Creating HTTPS configuration..."
    
    cat > /etc/nginx/sites-available/packet-inspection-transformer << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    # SSL settings
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }

    # Serve static files
    location / {
        root /opt/packet-inspection-transformer/dashboard/dist;
        index index.html;
        try_files \$uri \$uri/ /index.html;
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Health check
    location /health {
        access_log off;
        return 200 "OK";
        add_header Content-Type text/plain;
    }
}
EOF
    
    # Enable site
    ln -sf /etc/nginx/sites-available/packet-inspection-transformer /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Obtain certificate
    log_info "Obtaining SSL certificate from Let's Encrypt..."
    
    mkdir -p /var/www/html/.well-known/acme-challenge
    
    certbot certonly \
        --non-interactive \
        --agree-tos \
        --email "admin@$DOMAIN" \
        --webroot \
        -w /var/www/html \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" 2>/dev/null || {
        log_warn "Failed to obtain SSL certificate automatically"
        log_info "You can obtain it manually later with: sudo certbot --nginx -d $DOMAIN"
        # Keep HTTP config as fallback
        return
    }
    
    log_success "SSL certificate obtained for $DOMAIN"
    
    # Setup auto-renewal
    echo "0 0,12 * * * root certbot renew --quiet" > /etc/cron.d/certbot-renew
    chmod 644 /etc/cron.d/certbot-renew
    log_success "SSL auto-renewal configured"
}

# Create project directories
create_directories() {
    log_info "Creating project directories..."
    mkdir -p /opt/packet-inspection-transformer/{model,logs,dashboard}
    mkdir -p /etc/nginx/sites-available
    mkdir -p /etc/nginx/sites-enabled
    log_success "Directories created"
}

# Setup Python virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment..."
    
    VENV_PATH="/opt/packet-inspection-transformer/venv"
    
    if [ -d "$VENV_PATH" ]; then
        log_warn "Virtual environment already exists, skipping creation"
    else
        python3 -m venv "$VENV_PATH"
        log_success "Virtual environment created at $VENV_PATH"
    fi
    
    # Activate venv and install dependencies
    log_info "Installing Python dependencies..."
    source "$VENV_PATH/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip -q
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt -q
        log_success "Python dependencies installed"
    else
        log_warn "requirements.txt not found, skipping Python dependencies"
    fi
    
    deactivate
}

# Build frontend
build_frontend() {
    log_info "Building frontend..."
    
    FRONTEND_PATH="/opt/packet-inspection-transformer/dashboard"
    
    if [ ! -d "Frontend" ]; then
        log_warn "Frontend directory not found, skipping build"
        return
    fi
    
    cd Frontend
    
    # Install dependencies
    log_info "Installing frontend dependencies..."
    npm ci --quiet 2>/dev/null || npm install --quiet
    
    # Build
    log_info "Building frontend production bundle..."
    npm run build
    
    # Move build to dashboard folder
    rm -rf "$FRONTEND_PATH/dist"
    mv dist "$FRONTEND_PATH/dist"
    
    cd ..
    log_success "Frontend built and deployed to $FRONTEND_PATH/dist"
}

# Create nginx configuration
create_nginx_config() {
    log_info "Creating Nginx configuration..."
    
    # Get server IP or hostname
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
    
    cat > /etc/nginx/sites-available/packet-inspection-transformer << EOF
server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support for real-time features
    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }

    # Serve static files (frontend)
    location / {
        root /opt/packet-inspection-transformer/dashboard/dist;
        index index.html;
        try_files \$uri \$uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "OK";
        add_header Content-Type text/plain;
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/packet-inspection-transformer /etc/nginx/sites-enabled/
    
    # Remove default site if exists
    rm -f /etc/nginx/sites-enabled/default
    
    # Test nginx configuration
    nginx -t
    log_success "Nginx configuration created"
}

# Restart nginx
restart_nginx() {
    log_info "Restarting Nginx..."
    systemctl restart nginx
    systemctl status nginx --no-pager
    log_success "Nginx restarted"
}

# Create model directory placeholder
create_model_placeholder() {
    log_info "Creating model directory placeholder..."
    MODEL_PATH="/opt/packet-inspection-transformer/model"
    
    mkdir -p "$MODEL_PATH"
    
    # Create placeholder file
    cat > "$MODEL_PATH/README.md" << EOF
# Model Directory

This directory is for the ML model file.

## Required Model File

Please upload your trained model file as:

\`\`\`
finetuned_best_model.pth
\`\`\`

## Upload Instructions

You can upload the model using SCP:

\`\`\`bash
scp finetuned_best_model.pth user@<VM_IP>:/opt/packet-inspection-transformer/model/
\`\`\`

The model will be automatically loaded when the backend starts.
EOF

    log_success "Model directory created at $MODEL_PATH"
}

# Create systemd service file
create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/packet-inspection-transformer.service << EOF
[Unit]
Description=Packet Inspection Transformer - Malware Detection API
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/packet-inspection-transformer
Environment="PATH=/opt/packet-inspection-transformer/venv/bin"
Environment="PYTHONPATH=/opt/packet-inspection-transformer"
ExecStart=/opt/packet-inspection-transformer/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

# Logging
StandardOutput=append:/opt/packet-inspection-transformer/logs/uvicorn.log
StandardError=append:/opt/packet-inspection-transformer/logs/uvicorn.error.log

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/packet-inspection-transformer/logs /opt/packet-inspection-transformer/model

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_success "Systemd service created"
}

# Main setup function
main() {
    echo "=============================================="
    echo "  Packet Inspection Transformer - Setup"
    echo "=============================================="
    echo ""
    
    check_root
    update_system
    install_python
    install_nodejs
    install_nginx
    install_certbot
    create_directories
    setup_venv
    build_frontend
    create_model_placeholder
    create_systemd_service
    
    # Auto-setup SSL with optional domain
    log_info "============================================="
    log_info "SSL Configuration"
    log_info "============================================="
    auto_setup_ssl
    
    # Restart nginx
    log_info "Restarting Nginx..."
    systemctl restart nginx
    log_success "Nginx restarted"
    
    echo ""
    echo "=============================================="
    log_success "Setup completed successfully!"
    echo "=============================================="
    echo ""
    echo "Next steps:"
    echo "  1. Upload your model: scp finetuned_best_model.pth user@<VM_IP>:/opt/packet-inspection-transformer/model/"
    echo "  2. Run: sudo ./run.sh"
    echo "  3. Access dashboard:"
    echo "     - HTTP:  http://<VM_PUBLIC_IP>"
    echo "     - HTTPS: https://<VM_PUBLIC_IP> (if SSL configured)"
    echo ""
}

# Run main function
main "$@"