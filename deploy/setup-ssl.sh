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

# Check for domain name
check_domain() {
    log_info "Setting up Let's Encrypt SSL certificate..."
    
    # Get domain from user
    echo ""
    echo "=============================================="
    echo "  Let's Encrypt SSL Setup"
    echo "=============================================="
    echo ""
    echo "Note: You'll need a domain name pointing to this server's IP."
    echo ""
    
    read -p "Enter your domain name (e.g., example.com): " DOMAIN
    
    if [ -z "$DOMAIN" ]; then
        log_error "Domain name is required"
        exit 1
    fi
    
    log_info "Using domain: $DOMAIN"
}

# Verify DNS resolution
verify_dns() {
    log_info "Verifying DNS resolution for $DOMAIN..."
    
    IP=$(dig +short "$DOMAIN" A @8.8.8.8 2>/dev/null || host "$DOMAIN" 2>/dev/null | grep -oP '(?<=address )\d+\.\d+\.\d+\.\d+' || echo "")
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    
    if [ -z "$IP" ]; then
        log_error "Could not resolve DNS for $DOMAIN"
        log_info "Make sure your domain's A record points to: $SERVER_IP"
        exit 1
    fi
    
    log_info "Domain $DOMAIN resolves to: $IP"
    log_info "Server IP: $SERVER_IP"
    
    if [ "$IP" != "$SERVER_IP" ]; then
        log_warn "DNS IP ($IP) doesn't match server IP ($SERVER_IP)"
        log_warn "SSL certificate may not work correctly"
        read -p "Continue anyway? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            exit 1
        fi
    fi
}

# Stop nginx for certbot
stop_nginx() {
    log_info "Stopping nginx temporarily..."
    systemctl stop nginx
}

# Obtain certificate
obtain_cert() {
    log_info "Obtaining SSL certificate from Let's Encrypt..."
    
    # Create directories for verification
    mkdir -p /var/www/html/.well-known/acme-challenge
    
    # Use certbot to obtain certificate
    certbot certonly \
        --non-interactive \
        --agree-tos \
        --email "admin@$DOMAIN" \
        --webroot \
        -w /var/www/html \
        -d "$DOMAIN" \
        -d "www.$DOMAIN"
    
    log_success "Certificate obtained"
}

# Configure nginx for HTTPS
configure_https() {
    log_info "Configuring nginx for HTTPS..."
    
    cat > /etc/nginx/sites-available/packet-inspection-transformer << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }
    
    # Redirect to HTTPS
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;
    
    # SSL certificate
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # SSL configuration
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    
    # Modern SSL configuration
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
    
    # Remove default
    rm -f /etc/nginx/sites-enabled/default
    
    log_success "HTTPS configuration created"
}

# Start nginx
start_nginx() {
    log_info "Starting nginx..."
    
    # Test configuration
    nginx -t
    
    systemctl start nginx
    
    if systemctl is-active --quiet nginx; then
        log_success "Nginx started with HTTPS"
    else
        log_error "Failed to start nginx"
        exit 1
    fi
}

# Setup auto-renewal
setup_renewal() {
    log_info "Setting up automatic certificate renewal..."
    
    # Add cron job for renewal
    echo "0 0,12 * * * root certbot renew --quiet" > /etc/cron.d/certbot-renew
    chmod 644 /etc/cron.d/certbot-renew
    
    log_success "Auto-renewal configured (runs twice daily)"
}

# Main function
main() {
    echo "=============================================="
    echo "  Packet Inspection Transformer - SSL Setup"
    echo "=============================================="
    echo ""
    
    check_root
    check_domain
    verify_dns
    stop_nginx
    obtain_cert
    configure_https
    start_nginx
    setup_renewal
    
    echo ""
    echo "=============================================="
    log_success "SSL setup completed successfully!"
    echo "=============================================="
    echo ""
    echo "Your dashboard is now available at:"
    echo -e "  ${GREEN}https://$DOMAIN${NC}"
    echo ""
    echo "Certificate will automatically renew before expiration."
    echo ""
}

# Run main function
main "$@"