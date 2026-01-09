# Docker Deployment Guide

This guide explains how to deploy Packet Inspection Transformer using Docker containers.

## Prerequisites

- Docker installed on the server
- Docker Compose (v2.0+)
- Git to clone the repository
- Model file (uploaded via SCP)

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/hareesh08/PacketInspectionTransformerV3.git
cd PacketInspectionTransformerV3

# Create model directory
mkdir -p model

# Upload your model file
scp finetuned_best_model.pth user@<VM_IP>:/root/PacketInspectionTransformerV3/model/
```

### 2. Deploy with Docker

```bash
# Make deployment script executable
chmod +x deploy/docker-deploy.sh

# Build and start containers
sudo ./deploy/docker-deploy.sh build
sudo ./deploy/docker-deploy.sh up
```

### 3. Access the Application

- **Dashboard**: http://<VM_IP>
- **API**: http://<VM_IP>/api
- **Health**: http://<VM_IP>/health

## Available Commands

```bash
# Build images
sudo ./deploy/docker-deploy.sh build

# Start containers
sudo ./deploy/docker-deploy.sh up

# Stop containers
sudo ./deploy/docker-deploy.sh down

# Restart containers
sudo ./deploy/docker-deploy.sh restart

# View logs
sudo ./deploy/docker-deploy.sh logs

# Check status
sudo ./deploy/docker-deploy.sh status

# Clean up everything
sudo ./deploy/docker-deploy.sh clean
```

## Docker Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy                       │
│                      (Port 80/443)                           │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│   Backend Container     │   │   Nginx Container       │
│   - FastAPI + Uvicorn   │   │   - Static files        │
│   - Port: 8000          │   │   - API proxy           │
│   - Health check        │   │                        │
└─────────────────────────┘   └─────────────────────────┘
```

## Production Features

- **Auto-restart**: Containers restart on failure
- **Health checks**: Container health monitoring
- **Separate volumes**: Model and logs persistence
- **Network isolation**: Internal Docker network
- **Security**: Non-root user inside containers

## Model File

Place your trained model file at:
```
model/finetuned_best_model.pth
```

The model is mounted as a read-only volume inside the container.

## Logs

- **Backend logs**: `./logs/uvicorn.log`
- **Nginx logs**: `./logs/nginx/`

## SSL/HTTPS Setup

For production, add SSL certificates:

1. Obtain certificates from Let's Encrypt or your CA
2. Update `nginx.conf` to include SSL configuration
3. Map certificate files in `docker-compose.yml`
4. Restart containers

## Troubleshooting

### Container won't start
```bash
# Check logs
sudo ./deploy/docker-deploy.sh logs

# Check if ports are in use
sudo netstat -tulpn | grep :80
```

### Model not loading
```bash
# Verify model file exists
ls -la model/

# Check container mount
sudo docker exec -it packet-inspection-backend ls -la /app/model/
```

### Health check failing
```bash
# Test API directly
curl http://localhost:8000/health

# Check container health
sudo docker inspect packet-inspection-backend
```

## Update Deployment

```bash
# Pull latest code
git pull

# Rebuild and restart
sudo ./deploy/docker-deploy.sh down
sudo ./deploy/docker-deploy.sh build
sudo ./deploy/docker-deploy.sh up