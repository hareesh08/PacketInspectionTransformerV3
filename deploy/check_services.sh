#!/bin/bash

# Service Health Check Script
# This script checks if backend and frontend services are running properly

echo "=== Malware Detection Gateway Service Check ==="
echo

# Check if backend is running
echo "1. Checking Backend Service (Port 8000)..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is running and healthy"
    echo "   Backend URL: http://localhost:8000"
    echo "   Health endpoint: http://localhost:8000/health"
else
    echo "❌ Backend is not responding"
    echo "   Try starting with: ./start_backend.sh"
fi
echo

# Check if frontend is running
echo "2. Checking Frontend Service (Port 80)..."
if curl -s http://localhost/ > /dev/null; then
    echo "✅ Frontend is running"
    echo "   Frontend URL: http://localhost"
else
    echo "❌ Frontend is not responding"
    echo "   Try starting with: sudo ./start_frontend.sh"
fi
echo

# Check ports
echo "3. Checking Port Usage..."
echo "Processes using port 8000:"
sudo lsof -i :8000 2>/dev/null || echo "   No processes found on port 8000"
echo
echo "Processes using port 80:"
sudo lsof -i :80 2>/dev/null || echo "   No processes found on port 80"
echo

# Check external access
echo "4. Checking External Access..."
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "Unable to detect")
echo "   Public IP: $PUBLIC_IP"
echo "   External Backend URL: http://$PUBLIC_IP:8000"
echo "   External Frontend URL: http://$PUBLIC_IP"
echo

# Check firewall
echo "5. Checking Firewall..."
if command -v ufw &> /dev/null; then
    echo "UFW Status:"
    sudo ufw status
else
    echo "UFW not installed"
fi
echo

echo "=== Service Check Complete ==="