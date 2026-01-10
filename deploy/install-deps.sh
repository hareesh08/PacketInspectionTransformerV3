#!/bin/bash

# =============================================================================
# Dependency Installation Script
# =============================================================================
# This script installs all required dependencies for the project
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root (use sudo)"
   exit 1
fi

log_info "Installing system dependencies for Malware Detection Gateway..."

# Update system packages
log_info "Updating system packages..."
apt update && apt upgrade -y

# Install basic utilities
log_info "Installing basic utilities..."
apt install -y curl wget git htop unzip software-properties-common

# Install Python 3 and pip
log_info "Installing Python 3 and pip..."
apt install -y python3 python3-pip python3-venv python3-dev

# Install NVM and Node.js
log_info "Installing NVM and Node.js..."

# Install NVM
log_info "Installing NVM..."
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash

# Source NVM to make it available in current session
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# Install latest LTS Node.js
log_info "Installing Node.js LTS..."
nvm install --lts
nvm use --lts
nvm alias default lts/*

# Verify installation
log_info "Node.js version: $(node -v)"
log_info "NPM version: $(npm -v)"

# Install nginx
log_info "Installing nginx..."
apt install -y nginx

# Install PM2 globally
log_info "Installing PM2 process manager..."
npm install -g pm2

# Install serve for static file serving
log_info "Installing serve for static file serving..."
npm install -g serve

# Setup PM2 startup script
log_info "Setting up PM2 startup script..."
pm2 startup systemd -u root --hp /root

# Configure firewall (if ufw is available)
if command -v ufw &> /dev/null; then
    log_info "Configuring firewall..."
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
fi

# Create application directories
log_info "Creating application directories..."
mkdir -p /var/log/malware-detection
mkdir -p /var/lib/malware-detection
chown -R www-data:www-data /var/log/malware-detection
chown -R www-data:www-data /var/lib/malware-detection

log_success "All system dependencies installed successfully!"
echo
echo "Next steps:"
echo "1. Run: sudo ./start.sh fresh"
echo "2. Or manually install project dependencies with Python and Node.js"
echo
echo "Note: You may need to restart your terminal or run 'source ~/.bashrc' to use NVM in new sessions."