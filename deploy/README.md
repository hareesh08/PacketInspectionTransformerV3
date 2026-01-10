# Deployment Scripts

This directory contains all the deployment scripts and configurations for the Malware Detection Gateway.

## Quick Start

### 1. First Time Setup (Fresh Installation)

```bash
# Make scripts executable
chmod +x deploy/*.sh

# Install system dependencies (run as root)
sudo ./deploy/install-deps.sh

# Fresh installation with all dependencies
sudo ./deploy/start.sh fresh
```

### 2. Regular Operations

```bash
# Restart services
sudo ./deploy/start.sh restart

# Stop all services
sudo ./deploy/start.sh stop

# Check service status
./deploy/start.sh status

# View logs
./deploy/start.sh logs

# Clean cache and temporary files
./deploy/start.sh clean
```

## Files Description

### `start.sh` - Main Deployment Script
The primary script for managing the entire application.

**Commands:**
- `fresh` - Complete fresh installation with dependencies
- `restart` - Restart all services
- `stop` - Stop all services
- `clean` - Clean cache and temporary files
- `status` - Check service status
- `logs` - Show service logs

### `nginx.conf` - Nginx Configuration
Production-ready nginx configuration that:
- Serves the React frontend
- Proxies API requests to the backend
- Handles Server-Sent Events (SSE) for real-time notifications
- Implements rate limiting and security headers
- Optimizes static file serving

### `install-deps.sh` - System Dependencies Installer
Installs all required system dependencies:
- Python 3 and pip
- Node.js 18.x and npm
- Nginx web server
- PM2 process manager
- Other utilities

### `monitor.sh` - Service Monitoring
Health monitoring and automatic recovery:
- Monitors backend, frontend, and nginx
- Automatic service restart on failure
- System resource monitoring
- Continuous monitoring mode

## Architecture

```
Internet → Nginx (Port 80) → Frontend (Port 3000)
                           → Backend API (Port 8000)
```

### Service Management
- **Backend**: Managed by PM2 as `malware-backend`
- **Frontend**: Managed by PM2 as `malware-frontend`
- **Nginx**: Managed by systemd

### URL Structure
- Frontend: `http://your-server-ip/`
- API: `http://your-server-ip/api/*`
- Health Check: `http://your-server-ip/api/health`
- SSE Streams: `http://your-server-ip/api/notifications/stream`

## Configuration

### Environment Variables
The backend uses these environment variables (set automatically):
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
HOST=0.0.0.0
PORT=8000
```

### Frontend Configuration
Update `Frontend/.env` if needed:
```bash
VITE_API_URL=http://your-server-ip:8000
VITE_API_PORT=8000
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x deploy/*.sh
   sudo ./deploy/start.sh fresh
   ```

2. **Port Already in Use**
   ```bash
   sudo lsof -i :80
   sudo lsof -i :8000
   sudo kill -9 <PID>
   ```

3. **Nginx Configuration Error**
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

4. **PM2 Process Issues**
   ```bash
   pm2 list
   pm2 logs
   pm2 restart all
   ```

### Logs Location
- PM2 Logs: `~/.pm2/logs/`
- Nginx Logs: `/var/log/nginx/`
- Application Logs: `logs/` directory

### Service Status Commands
```bash
# Check all services
./deploy/start.sh status

# Monitor continuously
./deploy/monitor.sh continuous

# PM2 status
pm2 list
pm2 monit

# Nginx status
sudo systemctl status nginx
```

## Security Considerations

1. **Firewall**: Only ports 80 and 443 should be open to the internet
2. **Rate Limiting**: Configured in nginx for API endpoints
3. **File Upload Limits**: 100MB maximum file size
4. **Security Headers**: Implemented in nginx configuration

## Performance Tuning

### For High Traffic
1. Increase PM2 instances:
   ```bash
   pm2 scale malware-backend 4
   ```

2. Optimize nginx worker processes in `/etc/nginx/nginx.conf`:
   ```nginx
   worker_processes auto;
   worker_connections 1024;
   ```

3. Monitor resources:
   ```bash
   ./deploy/monitor.sh continuous 60
   ```

## Backup and Recovery

### Backup Important Data
```bash
# Database
cp data/threats.db backup/
# Logs
cp -r logs/ backup/
# Configuration
cp -r config/ backup/
```

### Recovery
```bash
# Restore and restart
sudo ./deploy/start.sh stop
# Restore files
sudo ./deploy/start.sh restart
```