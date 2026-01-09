# Packet Inspection Transformer - Deployment Guide

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Development](#development)
- [Production](#production)
- [Docker Commands](#docker-commands)
- [Environment Variables](#environment-variables)
- [SSL/HTTPS](#sslhttps)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Production Deployment

```bash
# 1. Clone the repository
git clone https://github.com/hareesh08/PacketInspectionTransformerV3.git
cd PacketInspectionTransformerV3

# 2. Build and start containers
make build
make up

# 3. Access the application
# Dashboard: http://localhost
# API: http://localhost/api
# Health: http://localhost/health
```

### Development

```bash
# Start development environment with hot reload
make up-dev

# Or using docker compose directly
docker compose --profile dev up -d
```

## Prerequisites

- Docker Engine 24.0+
- Docker Compose v2.20+
- Git
- 4GB RAM minimum (8GB recommended)
- 10GB disk space

## Development

### Using Makefile

```bash
# Start development environment
make up-dev

# Run tests
make test

# Run linters
make lint

# Build frontend
make build-frontend

# View logs
make logs
```

### Manual Docker Commands

```bash
# Start development container
docker compose --profile dev up -d

# Access the container
docker exec -it packet-inspection-dev bash

# Run tests inside container
docker exec packet-inspection-dev pytest tests/ -v
```

### Hot Reload

The development environment supports hot reload:
- Python code changes auto-reload the backend
- Frontend changes require manual rebuild (`make build-frontend`)

## Production

### Using Makefile

```bash
# Build all containers
make build

# Start production
make up

# Stop production
make down

# View status
make status

# Restart
make restart
```

### Manual Docker Commands

```bash
# Build images
docker compose build

# Start containers (production profile)
docker compose --profile prod up -d

# View logs
docker compose logs -f

# Stop containers
docker compose down
```

### Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | 8000 | Backend API port |
| `WEB_PORT` | 80 | Web server port |
| `DEV_PORT` | 8001 | Development port |
| `MALWARE_DETECTOR_DEBUG` | false | Enable debug mode |
| `MALWARE_DETECTOR_CONFIDENCE_THRESHOLD` | 0.7 | Detection threshold |

### Frontend Configuration

Configure the API URL in `Frontend/.env`:

```bash
cd Frontend
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | auto | API base URL |
| `VITE_API_PORT` | 8000 | API port |
| `VITE_PORT` | 8080 | Dev server port |

## Docker Commands

### Container Management

```bash
# Start all services
docker compose up -d

# Start specific profile
docker compose --profile prod up -d
docker compose --profile dev up -d

# Stop all services
docker compose down

# Restart services
docker compose restart

# View logs
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend
```

### Image Management

```bash
# Build images
docker compose build
docker compose build backend
docker compose build frontend

# Remove unused images
docker image prune -f

# Remove all project images
docker rmi packet-inspection-backend packet-inspection-frontend
```

### Cleanup

```bash
# Remove containers, networks, and volumes
docker compose down -v

# Full cleanup (including images)
make clean
```

## SSL/HTTPS

### Using Let's Encrypt

```bash
# Run SSL setup script
./deploy/setup-ssl.sh

# Or manually with certbot
certbot --nginx -d your-domain.com
```

### Manual SSL Configuration

1. Obtain certificates (Let's Encrypt, self-signed, or purchased)
2. Mount certificates in `docker-compose.yml`:

```yaml
services:
  frontend:
    volumes:
      - ./ssl:/ssl:ro
    environment:
      - SSL_CERT_PATH=/ssl/fullchain.pem
      - SSL_KEY_PATH=/ssl/privkey.pem
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs

# Check if ports are in use
netstat -tulpn | grep :80
```

### Model not loading

```bash
# Verify model file exists
ls -la model/

# Check container mount
docker exec packet-inspection-backend ls -la /app/model/
```

### Health check failing

```bash
# Test API directly
curl http://localhost:8000/health

# Check container health
docker inspect packet-inspection-backend
```

### Frontend can't connect to backend

```bash
# Check nginx logs
docker exec packet-inspection-nginx cat /var/log/nginx/error.log

# Verify backend is healthy
docker exec packet-inspection-backend curl http://localhost:8000/health
```

### Port already in use

```bash
# Find process using port
lsof -i :80

# Kill the process
kill <PID>
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy                       │
│                      (Port 80/443)                           │
└─────────────────────────────────────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│   Backend Container     │   │   Frontend Container    │
│   - FastAPI + Uvicorn   │   │   - Nginx + Static      │
│   - Port: 8000          │   │   - Port: 80            │
│   - Health check        │   │                         │
└─────────────────────────┘   └─────────────────────────┘
```

## File Structure

```
PacketInspectionTransformerV3/
├── .github/workflows/     # GitHub Actions CI/CD
├── .dockerignore          # Files to exclude from build
├── Dockerfile             # Backend production build
├── Dockerfile.dev         # Development environment
├── Frontend/
│   ├── Dockerfile         # Frontend multi-stage build
│   ├── .env.example       # Frontend environment template
│   └── src/               # React frontend source
├── docker-compose.yml     # Production compose
├── deploy/
│   ├── docker-deploy.sh   # Docker deployment script
│   ├── setup.sh           # Server setup script
│   └── setup-ssl.sh       # SSL setup script
├── Makefile               # Common commands
├── model/                 # ML model files
├── logs/                  # Application logs
└── tests/                 # Backend tests
```

## CI/CD Pipeline

### GitHub Actions

- **CI**: Runs on every push/PR (tests, lint, security scan)
- **CD**: Runs on version tags (build, push, deploy)

### Manual Deployment

```bash
# Tag and push
git tag v1.0.0
git push origin v1.0.0

# Or trigger via GitHub UI
# Go to Actions > CD > Run workflow
```

## Support

For issues and questions:
- Open a GitHub issue
- Check the logs: `make logs`
- Review [Troubleshooting](#troubleshooting) section