# Packet Inspection Transformer - Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [SSL Certificate Setup](#ssl-certificate-setup)
6. [Deployment Options](#deployment-options)
7. [Scaling](#scaling)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Security](#security)

---

## Overview

This guide provides comprehensive instructions for deploying the Packet Inspection Transformer (PIT) application in production environments. The application consists of:

- **Frontend**: React-based UI served via Nginx
- **Backend**: FastAPI application with PyTorch-based malware detection
- **Reverse Proxy**: Nginx with SSL termination
- **SSL Certificates**: Let's Encrypt with automatic renewal

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Load Balancer                            │
│                    (Cloud or Nginx/Traefik)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx Reverse Proxy                       │
│              (SSL Termination, Rate Limiting, Caching)           │
└─────────────────────────────────────────────────────────────────┘
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
┌────────────────────────┐    ┌────────────────────────┐
│   Frontend (React)     │    │    Backend (FastAPI)   │
│    Port: 80/443        │    │     Port: 8000         │
└────────────────────────┘    └────────────────────────┘
```

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| Memory | 4 GB | 8+ GB |
| Storage | 20 GB SSD | 50+ GB SSD |
| Docker | 20.10+ | Latest |
| Docker Compose | 2.0+ | Latest |

### Required Software

1. **Docker Engine** - [Install Guide](https://docs.docker.com/engine/install/)
2. **Docker Compose** - [Install Guide](https://docs.docker.com/compose/install/)
3. **Git** - For repository cloning
4. **OpenSSL** - For certificate management (optional)

### Network Requirements

- Port 80 (HTTP) - Required for Let's Encrypt verification
- Port 443 (HTTPS) - Production traffic
- Outbound access to Docker Hub/GHCR for image pulls

### Cloud-Specific Requirements

**AWS:**
- EC2 instance (t3.medium or larger recommended)
- Security group with inbound rules for 80, 443
- Elastic IP (optional, for static IP)

**Azure:**
- Virtual Machine (Standard B2s or larger)
- Network Security Group with inbound rules for 80, 443
- Public IP address

**GCP:**
- Compute Engine instance (e2-medium or larger)
- Firewall rules for ports 80, 443
- Static external IP

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/packet-inspection-transformer.git
cd packet-inspection-transformer
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
nano .env
```

### 3. Generate SSL Certificates (Staging)

```bash
# For testing/staging (Let's Encrypt staging)
docker run --rm \
  -v nginx/certificates:/etc/letsencrypt \
  -v nginx/html:/var/www/html \
  certbot/certbot certonly \
  --webroot \
  --webroot-path /var/www/html \
  --email admin@example.com \
  --agree-tos \
  --staging \
  -d your-domain.com
```

### 4. Start Application

```bash
# Build and start containers
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 5. Verify Deployment

```bash
# Health check
curl https://your-domain.com/health

# Expected response:
# {"status": "healthy", "model": {...}, "database": {...}}
```

---

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Application Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=2

# Model Configuration
MODEL_PATH=/app/model/finetuned_best_model.pth
VOCAB_SIZE=30000
D_MODEL=256
NHEAD=8
NUM_LAYERS=6
DIM_FEEDFORWARD=1024
DROPOUT=0.1

# Detection Settings
CONFIDENCE_THRESHOLD=0.85
MAX_FILE_SIZE=104857600

# SSL Configuration
DOMAIN=your-domain.com
LETSENCRYPT_EMAIL=admin@your-domain.com
```

### Model Configuration

The application requires a trained model file at the specified path:

```bash
# Verify model file exists
ls -la model/finetuned_best_model.pth
```

If the model file is missing:
1. Train a model using the provided training scripts
2. Or download a pre-trained model from the releases page

### Nginx Configuration

Customize [`nginx/conf.d/default.conf`](../nginx/conf.d/default.conf):

```nginx
# Adjust rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# Adjust file upload size
client_max_body_size 100M;

# Customize SSL protocols (if needed)
ssl_protocols TLSv1.2 TLSv1.3;
```

### CORS Configuration

For development or multi-domain setups, set CORS origins:

```bash
CORS_ORIGINS=https://domain1.com,https://domain2.com
```

---

## SSL Certificate Setup

### Option 1: Let's Encrypt (Recommended)

#### Automated Setup

The application includes a certbot container for automatic certificate renewal:

```bash
# Set environment variables
export DOMAIN=your-domain.com
export LETSENCRYPT_EMAIL=admin@your-domain.com

# Generate initial certificate
docker compose run --rm certbot

# Start automatic renewal
docker compose up -d certbot
```

#### Manual Setup

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d your-domain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

#### Certificate Renewal Cron Job

Add to crontab (`crontab -e`):

```bash
# Renew certificate daily at 2 AM
0 2 * * * /usr/bin/docker restart pit-certbot 2>/dev/null || true
```

### Option 2: Self-Signed Certificate (Testing Only)

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certificates/privkey.pem \
  -out nginx/certificates/fullchain.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"
```

### Option 3: Cloud-Managed Certificates

For AWS, Azure, or GCP, use their respective certificate managers:

**AWS ACM:**
1. Request certificate in AWS Certificate Manager
2. Verify domain ownership
3. Update load balancer to use ACM certificate

**Azure App Service:**
1. Configure custom domain
2. Upload certificate or use managed certificate
3. Enable HTTPS

---

## Deployment Options

### Single Server Deployment

The standard deployment using Docker Compose:

```bash
# Deploy
docker compose up -d

# View logs
docker compose logs -f

# Scale workers
docker compose up -d --scale backend=2
```

### Docker Swarm Mode

For high availability across multiple servers:

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml pit-stack

# Scale services
docker service scale pit_stack_backend=3
docker service scale pit_stack_frontend=2
```

### Kubernetes Deployment

For Kubernetes environments, see the [K8s deployment guide](k8s/README.md):

```bash
# Apply configurations
kubectl apply -f k8s/

# Check status
kubectl get pods
kubectl get services
```

### Cloud Platform Deployment

#### AWS ECS

1. Push images to ECR
2. Create ECS cluster
3. Configure task definition
4. Set up ALB with ACM certificate
5. Deploy service

#### Azure Container Apps

1. Push images to Azure Container Registry
2. Create Container App environment
3. Deploy with Azure CLI

#### GCP Cloud Run

```bash
# Deploy backend
gcloud run deploy pit-backend \
  --image gcr.io/project/pit-backend:latest \
  --platform managed \
  --region us-central1

# Deploy frontend (with Cloud Run revisions)
gcloud run deploy pit-frontend \
  --image gcr.io/project/pit-frontend:latest \
  --platform managed \
  --region us-central1
```

---

## Scaling

### Horizontal Scaling

#### Backend Scaling

```bash
# Scale backend instances
docker compose up -d --scale backend=3

# Verify instances
docker compose ps
```

#### Load Balancer Configuration

For production deployments, configure a load balancer:

**Nginx Upstream:**
```nginx
upstream backend_cluster {
    least_conn;
    server backend1:8000 weight=1;
    server backend2:8000 weight=1;
    server backend3:8000 weight=1;
    keepalive 32;
}
```

**Cloud Load Balancer:**
1. Create target group with backend instances
2. Configure health checks
3. Attach to load balancer
4. Set up SSL termination

### Vertical Scaling

Increase resource allocation in docker-compose.yml:

```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 8G
      reservations:
        cpus: '2'
        memory: 4G
```

### Database Scaling

For high-traffic deployments, migrate to PostgreSQL:

```bash
# Update environment
DATABASE_URL=postgresql://user:password@postgres:5432/pit_db

# Use PostgreSQL compose file
docker compose -f docker-compose.postgres.yml up -d
```

### Session Management

For multi-instance deployments, use Redis for sessions:

```bash
# Add Redis service
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"

# Update backend configuration
SESSION_REDIS_URL=redis://redis:6379/0
```

---

## Monitoring

### Health Checks

The application exposes several health endpoints:

```bash
# Overall health
curl https://your-domain.com/health

# Model information
curl https://your-domain.com/model-info

# System statistics
curl https://your-domain.com/stats
```

### Logging

View logs with Docker:

```bash
# All containers
docker compose logs

# Specific service
docker compose logs backend
docker compose logs frontend

# Follow logs
docker compose logs -f
```

### Metrics Integration

Configure Prometheus metrics endpoint (if implemented):

```yaml
backend:
  environment:
    - PROMETHEUS_ENABLED=true
    - METRICS_PORT=9090
```

### Third-Party Monitoring

**Grafana + Prometheus:**
1. Enable metrics endpoint
2. Configure Prometheus to scrape
3. Import dashboards

**Datadog:**
1. Install Datadog agent
2. Enable Docker integration
3. Configure log collection

---

## Troubleshooting

### Common Issues

#### 1. Container Fails to Start

```bash
# Check logs
docker compose logs backend

# Common causes:
# - Missing model file
# - Incorrect permissions
# - Port already in use

# Verify model file
ls -la model/

# Check port usage
netstat -tlnp | grep 8000
```

#### 2. SSL Certificate Issues

```bash
# Check certificate status
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Verify certificate files
ls -la nginx/certificates/live/

# Regenerate certificate
docker compose run --rm certbot
```

#### 3. Backend Health Check Fails

```bash
# Test directly
curl http://localhost:8000/health

# Check container networking
docker compose exec backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Verify environment
docker compose exec backend env | grep -E "MODEL|PATH|DATABASE"
```

#### 4. Frontend Returns 502/503

```bash
# Check Nginx logs
docker compose logs frontend

# Verify backend is running
docker compose ps

# Test backend connectivity
docker compose exec frontend curl http://backend:8000/health
```

#### 5. File Upload Fails

```bash
# Check size limits
curl -X POST -F "file=@test.pdf" https://your-domain.com/scan/file

# Verify configuration
docker compose exec backend python -c "from settings import settings; print(settings.max_file_size)"

# Check Nginx limits
grep client_max_body_size nginx/conf.d/default.conf
```

### Performance Tuning

#### Backend Optimization

```yaml
# Increase workers based on CPU cores
environment:
  - WORKERS=4
  - UVICORN_WORKERS=4

# GPU configuration
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

#### Nginx Optimization

```nginx
# Increase worker connections
events {
    worker_connections 4096;
}

# Enable gzip compression
gzip on;
gzip_comp_level 6;
gzip_min_length 1024;
```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Set environment
DEBUG=true
LOG_LEVEL=debug

# Restart services
docker compose restart backend
```

### Getting Help

1. Check application logs
2. Review Nginx error logs
3. Verify configuration files
4. Test individual components
5. Search existing issues

---

## Security

### Production Hardening

1. **Disable Debug Mode**
   ```bash
   DEBUG=false
   ```

2. **Restrict CORS**
   ```bash
   CORS_ORIGINS=https://your-domain.com
   ```

3. **Enable Firewall**
   ```bash
   # UFW example
   sudo ufw allow 22
   sudo ufw allow 80
   sudo ufw allow 443
   sudo ufw enable
   ```

4. **Set File Permissions**
   ```bash
   chmod 600 .env
   chmod 600 nginx/certificates/privkey.pem
   ```

### Docker Security

```bash
# Enable Docker daemon security
dockerd --seccomp-profile=default

# Use security options
docker compose config --security-opt seccomp=profile.json
```

### Network Security

1. Use TLS 1.2+ only
2. Enable HSTS
3. Configure CSP headers
4. Use rate limiting
5. Enable DDoS protection (cloud provider)

### Secret Management

For production, use secret management tools:

**HashiCorp Vault:**
```bash
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=your-token
```

**AWS Secrets Manager:**
```bash
aws secretsmanager get-secret-value --secret-id pit/api-key
```

### Compliance

- Enable audit logging
- Configure log retention
- Set up alerting
- Regular security scans

---

## Maintenance

### Updates

```bash
# Pull latest images
docker compose pull

# Backup database
docker compose exec backend cp /app/data/threats.db /app/data/threats_backup.db

# Restart with new images
docker compose up -d

# Verify deployment
curl https://your-domain.com/health
```

### Backup

```bash
# Backup database
docker compose exec backend tar czf /tmp/backup.tar.gz /app/data

# Copy to host
docker cp pit-backend:/tmp/backup.tar.gz ./backup.tar.gz
```

### Rollback

```bash
# List previous images
docker images | grep pit

# Rollback to previous version
docker tag previous-image:latest pit-backend:current
docker compose restart backend
```

---

## Quick Reference

### Essential Commands

```bash
# Start
docker compose up -d

# Stop
docker compose down

# Restart
docker compose restart

# View logs
docker compose logs -f

# Scale
docker compose up -d --scale backend=3

# Update
docker compose pull && docker compose up -d
```

### File Locations

| Purpose | Location |
|---------|----------|
| Config | `./config/` |
| Logs | `./logs/` |
| Data | `./data/` |
| Certificates | `./nginx/certificates/` |
| Nginx config | `./nginx/conf.d/` |

### Ports

| Service | Port | Protocol |
|---------|------|----------|
| HTTP | 80 | TCP |
| HTTPS | 443 | TCP |
| Backend API | 8000 | TCP |

---

## Support

For issues and questions:

1. Check the [FAQ](#troubleshooting)
2. Search existing issues
3. Open a new issue with:
   - Environment details
   - Error logs
   - Steps to reproduce
4. Contact: support@example.com

---

---

## Appendix: IP-Based Deployment Troubleshooting

### Problem Summary

**Initial State:** Application deployment failed with frontend (pit-frontend) and certbot (pit-certbot) containers in constant crash-restart loop.

**Root Cause:** The Nginx configuration was hardcoded to use HTTPS/SSL with Let's Encrypt certificates pointing to an IP address (206.189.138.156), which is impossible because Let's Encrypt only issues certificates for domain names, not raw IP addresses.

**Symptoms:**
- Frontend logs showed: `cannot load certificate "/etc/letsencrypt/live/206.189.138.156/fullchain.pem": No such file or directory`
- Containers restarting every few seconds
- Application inaccessible via browser

### Complete Fix Applied

#### 1. Stop Crashing Containers

```bash
docker stop pit-frontend pit-certbot
docker rm pit-frontend pit-certbot
```

#### 2. Create HTTP-Only Nginx Configuration

Use the provided `nginx-http.conf` in project root:

```bash
docker run -d \
  --name pit-frontend \
  --network packetinspectiontransformerv3_pit-network \
  -p 80:80 \
  -v $(pwd)/nginx-http.conf:/etc/nginx/conf.d/default.conf \
  packetinspectiontransformerv3-frontend
```

#### 3. Verify Deployment

```bash
# Check container status
docker ps

# Test locally
curl -v http://localhost
```

### Final Working State

| Container | Status | Ports | Health |
|-----------|--------|-------|--------|
| pit-frontend | ✅ Running | 0.0.0.0:80->80/tcp | Healthy |
| pit-backend | ✅ Running | 0.0.0.0:8000->8000/tcp | Healthy |

### Access URLs

| Service | URL |
|---------|-----|
| Frontend Application | http://206.189.138.156 |
| Backend API | http://206.189.138.156:8000 |
| API Documentation | http://206.189.138.156:8000/docs |

### Key Technical Insights

#### Why SSL Failed with IP Address

- **Let's Encrypt Policy:** Cannot issue certificates for IP addresses
- **Certificate Validation:** Requires domain ownership verification via DNS or HTTP challenges
- **Configuration Lock:** Original Nginx config had no fallback mechanism for missing certificates

#### Network Architecture

```
User Browser → (Port 80) → pit-frontend (Nginx) → /api/ → pit-backend (Port 8000)
                                   ↓
                         Static Files (/usr/share/nginx/html)
```

#### Docker Network Configuration

- **Network:** `packetinspectiontransformerv3_pit-network` (user-defined bridge)
- **Container-to-container communication:** Via service names (`pit-backend:8000`)
- **Host port mapping:** `80:80` (frontend), `8000:8000` (backend)

### Troubleshooting Commands Reference

#### Basic Diagnostics

```bash
# Check container status
docker ps -a

# View container logs
docker logs pit-frontend
docker logs pit-backend

# Test connectivity between containers
docker exec pit-frontend curl -v http://pit-backend:8000/

# Check Nginx configuration
docker exec pit-frontend nginx -t
```

#### Network Troubleshooting

```bash
# Inspect network configuration
docker network inspect packetinspectiontransformerv3_pit-network

# Test port accessibility from host
curl -v http://localhost:80
curl -v http://localhost:8000

# Check firewall status
sudo ufw status
```

#### Configuration Validation

```bash
# Verify mounted Nginx config
docker exec pit-frontend cat /etc/nginx/conf.d/default.conf

# Check frontend build files
docker exec pit-frontend ls -la /usr/share/nginx/html/
```

### Common Issues & Solutions

#### Issue 1: "Backend not connected" in Frontend

**Cause:** Frontend making requests to wrong URL or Nginx proxy misconfigured

**Solution:**

Check frontend API client configuration and verify Nginx proxy_pass directive:

```bash
docker exec pit-frontend cat /etc/nginx/conf.d/default.conf | grep -A5 "location /api/"
```

Ensure requests go to `/api/` endpoint, not direct backend URL.

#### Issue 2: Frontend Container Won't Start

```bash
# Force remove and recreate
docker rm -f pit-frontend
docker run -d \
  --name pit-frontend \
  --network packetinspectiontransformerv3_pit-network \
  -p 80:80 \
  -v $(pwd)/nginx-http.conf:/etc/nginx/conf.d/default.conf \
  packetinspectiontransformerv3-frontend
```

#### Issue 3: Port Already in Use

```bash
# Find process using port 80
sudo lsof -i :80

# Kill conflicting process or change Nginx port in docker run command
# Change -p 80:80 to -p 8080:80 for alternative port
```

### Migration to Production (When Ready)

#### With Domain Name

1. Get a domain and point A record to 206.189.138.156
2. Update Nginx config to use domain in `server_name`
3. Re-enable SSL configuration with Let's Encrypt
4. Use certbot container properly with domain validation

#### Production Nginx Template

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # ... rest of configuration
}
```

### Deployment Checklist

- [ ] Backend container running on port 8000
- [ ] Frontend container running on port 80 with HTTP config
- [ ] Docker network properly configured
- [ ] Nginx proxy passing `/api/` to backend
- [ ] Static files served from `/usr/share/nginx/html`
- [ ] SPA routing working (try_files directive)
- [ ] Firewall allows ports 80 and 8000
- [ ] (Optional) Configure domain name for SSL
- [ ] (Optional) Set up HTTPS for production

### Best Practices for Future Deployments

1. **Environment-Specific Configs:** Maintain separate configurations for dev/staging/prod
2. **Health Checks:** Implement `/health` endpoints in both frontend and backend
3. **Logging:** Centralize Docker container logs for monitoring
4. **Backup Configs:** Keep nginx-http.conf and other config files in version control
5. **Documentation:** Update this guide with any environment-specific changes

---

**Last Updated:** 2024-01-10
**Version:** 1.0.1
**Status:** ✅ OPERATIONAL (HTTP mode)
**Note:** For production use, acquire a domain name and implement HTTPS. The current HTTP configuration is suitable for development and testing purposes.