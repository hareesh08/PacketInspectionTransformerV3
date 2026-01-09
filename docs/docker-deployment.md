# Docker Deployment Guide

This guide explains how to deploy Packet Inspection Transformer using Docker containers.

## Prerequisites

- Ubuntu/Debian Linux server
- Git to clone the repository
- Model file (uploaded via SCP)
- SSH access to the VM

## Quick Start

### 1. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/hareesh08/PacketInspectionTransformerV3.git
cd PacketInspectionTransformerV3
```

### 2. Upload Files to Server

From your local machine, upload the model and deploy scripts:

```bash
# Upload the model file
scp model/finetuned_best_model.pth root@<VM_IP>:/root/PacketInspectionTransformerV3/model/

# Upload the deploy directory
scp -r deploy root@<VM_IP>:/root/PacketInspectionTransformerV3/

# Or using the full local path (Windows PowerShell):
scp "D:\Python-25\PacketInspectionTransformerV3\model\finetuned_best_model.pth" root@<VM_IP>:/root/PacketInspectionTransformerV3/model/
scp -r "D:\Python-25\PacketInspectionTransformerV3\deploy" root@<VM_IP>:/root/PacketInspectionTransformerV3/
```

**Example with actual IP:**
```bash
scp model/finetuned_best_model.pth root@157.245.97.220:/root/PacketInspectionTransformerV3/model/
scp -r deploy root@157.245.97.220:/root/PacketInspectionTransformerV3/
```

### 3. Prepare the Server

SSH into the server and run:

```bash
ssh root@<VM_IP>

# Navigate to project directory
cd ~/PacketInspectionTransformerV3

# Clean up old files if needed
rm -rf threats.db

# Pull latest code
git pull

# If there are local changes causing conflicts:
# git stash
# git pull
# git stash pop  # (if you want to keep local changes)
```

### 2. Install Docker (Auto-Install)

```bash
# Make deployment script executable
chmod +x deploy/docker-deploy.sh

# Install Docker and Docker Compose (if not already installed)
sudo ./deploy/docker-deploy.sh install
```

### 3. Deploy with Docker

```bash
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
# Install Docker (run once)
sudo ./deploy/docker-deploy.sh install

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

### Frontend shows "Failed to connect to backend"

This usually happens when the frontend API URL is pointing to localhost instead of the server IP.

**Check and fix the API URL:**

1. Edit `Frontend/.env`:
```bash
# Change from:
VITE_API_URL=http://localhost:8000
# To:
VITE_API_URL=http://157.245.97.220
```

2. Commit and push the change:
```bash
git add Frontend/.env
git commit -m "Fix API URL for production"
git push
```

3. On the server, pull and rebuild:
```bash
cd ~/PacketInspectionTransformerV3
git pull
sudo ./deploy/docker-deploy.sh build
sudo ./deploy/docker-deploy.sh down
sudo ./deploy/docker-deploy.sh up
```

### Port 80 already in use

If nginx fails to start due to port conflict:

```bash
# Stop host nginx
sudo systemctl stop nginx

# Restart containers
sudo ./deploy/docker-deploy.sh down
sudo ./deploy/docker-deploy.sh up
```

## Update Deployment

```bash
# Navigate to project directory
cd ~/PacketInspectionTransformerV3

# Check for local changes that might conflict
git status

# If there are local changes causing conflicts:
git stash
git pull
git stash pop  # (if you want to keep local changes)

# If no conflicts:
git pull

# Rebuild and restart
sudo ./deploy/docker-deploy.sh down
sudo ./deploy/docker-deploy.sh build
sudo ./deploy/docker-deploy.sh up
```

### Handling Git Conflicts

If `git pull` fails due to local changes:

```bash
# Stash local changes
git stash

# Pull latest
git pull

# Check what changed
git diff stash@{0}

# Apply stash if changes are needed, or drop to discard
git stash pop  # Apply and remove stash
# OR
git stash drop  # Remove stash without applying
```

## File Transfer Commands

Quick reference for transferring files from local machine to server:

```bash
# Upload model file
scp model/finetuned_best_model.pth root@<VM_IP>:/root/PacketInspectionTransformerV3/model/

# Upload deploy directory
scp -r deploy root@<VM_IP>:/root/PacketInspectionTransformerV3/

# Upload entire project
scp -r . root@<VM_IP>:/root/PacketInspectionTransformerV3/ --exclude='.git' --exclude='node_modules' --exclude='Frontend/node_modules'

# Download logs from server
scp root@<VM_IP>:/root/PacketInspectionTransformerV3/logs/ ./logs/
```

## Server IP Reference

| Server | IP |
|--------|-----|
| Primary VM | 157.245.97.220 |
| Secondary VM | 143.110.241.116 |

## Auto-Install Details

The deployment script automatically installs:

- **Docker Engine** - Latest stable version from official repository
- **Docker Compose** - V2 plugin for container orchestration
- **Required dependencies** - curl, ca-certificates, gnupg, lsb-release

The installation:
1. Adds Docker's official GPG key
2. Adds Docker repository to apt sources
3. Installs Docker CE, CLI, and containerd
4. Sets up Docker Compose
5. Adds user to docker group (logout/login required for group changes)
6. Starts Docker daemon