#!/bin/bash

# =============================================================================
# Quick Fix Script - Resolve Backend Connection Issues
# =============================================================================
# This script fixes the connection between frontend and backend by ensuring
# both containers are on the same Docker network
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "============================================================================="
echo "            ${GREEN}Backend Connection Fix Script${NC}"
echo "============================================================================="
echo ""

# Step 1: Stop manually started frontend
echo -e "${YELLOW}Step 1:${NC} Stopping manually started frontend..."
docker stop pit-frontend 2>/dev/null && echo "  - Stopped pit-frontend" || echo "  - pit-frontend not running"
docker rm pit-frontend 2>/dev/null && echo "  - Removed pit-frontend" || echo "  - pit-frontend not found"
echo ""

# Step 2: Check if backend is running
echo -e "${YELLOW}Step 2:${NC} Checking backend status..."
if docker ps --filter "name=pit-backend" --format "{{.Names}}" | grep -q "pit-backend"; then
    echo -e "  ${GREEN}✓${NC} Backend is running"
    docker ps --filter "name=pit-backend" --format "  {{.Names}}: {{.Status}} {{.Ports}}"
else
    echo -e "  ${RED}✗${NC} Backend is not running!"
    echo "  Starting backend with docker compose..."
    docker compose up -d backend
fi
echo ""

# Step 3: Ensure network exists
echo -e "${YELLOW}Step 3:${NC} Checking Docker network..."
NETWORK_NAME="pit-network"
if docker network inspect ${NETWORK_NAME} &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Network '${NETWORK_NAME}' exists"
else
    echo -e "  ${YELLOW}!${NC} Network '${NETWORK_NAME}' not found, creating..."
    docker network create ${NETWORK_NAME} 2>/dev/null || true
fi
echo ""

# Step 4: Connect backend to network if not already
echo -e "${YELLOW}Step 4:${NC} Ensuring backend is on correct network..."
BACKEND_CONTAINER=$(docker ps --filter "name=pit-backend" -q | head -1)
if [[ -n "$BACKEND_CONTAINER" ]]; then
    if docker network inspect ${NETWORK_NAME} --format '{{range .Containers}} {{.Name}} {{end}}' | grep -q "pit-backend"; then
        echo -e "  ${GREEN}✓${NC} Backend is on '${NETWORK_NAME}' network"
    else
        echo "  Connecting backend to '${NETWORK_NAME}' network..."
        docker network connect ${NETWORK_NAME} pit-backend 2>/dev/null || echo "  Already connected or not needed"
    fi
fi
echo ""

# Step 5: Start frontend with docker compose
echo -e "${YELLOW}Step 5:${NC} Starting frontend with docker compose..."
docker compose up -d frontend
echo ""

# Step 6: Wait for services
echo -e "${YELLOW}Step 6:${NC} Waiting for services to be ready..."
sleep 5
echo ""

# Step 7: Verify connection
echo -e "${YELLOW}Step 7:${NC} Verifying backend connection from frontend..."
FRONTEND_CONTAINER=$(docker ps --filter "name=pit-frontend" -q | head -1)
if [[ -n "$FRONTEND_CONTAINER" ]]; then
    echo "  Testing connection from frontend to backend..."
    if docker exec $FRONTEND_CONTAINER curl -sf --connect-timeout 5 http://pit-backend:8000/health &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Backend is reachable from frontend!"
    else
        echo -e "  ${RED}✗${NC} Cannot connect to backend from frontend"
        echo "  Checking network configuration..."
        docker network inspect ${NETWORK_NAME} 2>/dev/null | grep -A5 Containers || echo "  Network inspection failed"
    fi
else
    echo -e "  ${RED}✗${NC} Frontend container not found"
fi
echo ""

# Step 8: Test local access
echo -e "${YELLOW}Step 8:${NC} Testing local access..."
echo "  Backend health: $(curl -sf http://localhost:8000/health 2>/dev/null | head -c 100 || echo 'FAILED')"
echo "  Frontend:       $(curl -sf http://localhost:80/ 2>/dev/null | head -c 100 || echo 'FAILED')"
echo ""

# Summary
echo "============================================================================="
echo "                    ${GREEN}FIX COMPLETE${NC}"
echo "============================================================================="
echo ""
echo "Access URLs:"
echo "  Frontend: http://localhost:80"
echo "  Backend:  http://localhost:8000"
echo "  Health:   http://localhost:8000/health"
echo ""
echo "If issues persist, check:"
echo "  docker compose logs frontend"
echo "  docker compose logs backend"
echo "  docker network inspect pit-network"
echo ""