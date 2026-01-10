#!/bin/bash

# =============================================================================
# Fix nginx configuration to serve the frontend properly
# =============================================================================

set -e

PROJECT_ROOT="/root/PacketInspectionTransformerV3"
FRONTEND_DIR="$PROJECT_ROOT/Frontend"

echo "Fixing nginx configuration..."

# Create frontend directory
mkdir -p /var/www/malware-detection/html

# Copy frontend dist files to nginx directory
if [ -d "$FRONTEND_DIR/dist" ]; then
    echo "Copying frontend files to /var/www/malware-detection/html..."
    cp -r "$FRONTEND_DIR/dist/"* /var/www/malware-detection/html/
else
    echo "ERROR: Frontend dist directory not found at $FRONTEND_DIR/dist"
    echo "Please build the frontend first: cd $FRONTEND_DIR && npm run build"
    exit 1
fi

# Copy the nginx config
echo "Copying nginx configuration..."
cp "$PROJECT_ROOT/deploy/nginx.conf" /etc/nginx/sites-available/malware-detection

# Remove old symlink and create new one
rm -f /etc/nginx/sites-enabled/malware-detection
ln -sf /etc/nginx/sites-available/malware-detection /etc/nginx/sites-enabled/

# Remove default nginx site
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

echo "Nginx configuration fixed. Reloading..."
systemctl reload nginx

echo ""
echo "=== Frontend should now be accessible at http://64.227.150.240 ==="
echo ""
echo "Testing access..."
curl -s http://localhost/ | head -20