# Server Deployment Guide

## Quick Setup on Ubuntu Server

### 1. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip -y

# Install Node.js and npm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Install nginx (optional, for production)
sudo apt install nginx -y
```

### 2. Clone and Setup Project

```bash
# Clone your repository
git clone <your-repo-url>
cd <your-project-directory>

# Make scripts executable
chmod +x start_backend.sh
chmod +x start_frontend.sh
```

### 3. Start Backend Server

```bash
# Start backend (runs on port 8000)
./start_backend.sh
```

### 4. Start Frontend Server (in another terminal)

```bash
# Start frontend (runs on port 80)
sudo ./start_frontend.sh
```

## Troubleshooting

### Backend Issues

1. **Port 8000 already in use:**
   ```bash
   sudo lsof -i :8000
   sudo kill -9 <PID>
   ```

2. **Python dependencies missing:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Model file missing:**
   - Make sure you have the model file in the `model/` directory
   - Check the path in `settings.py`

### Frontend Issues

1. **Port 80 permission denied:**
   ```bash
   sudo ./start_frontend.sh
   ```

2. **Node.js dependencies missing:**
   ```bash
   cd Frontend
   npm install
   ```

3. **Build fails:**
   ```bash
   cd Frontend
   npm run build
   ```

### Network Issues

1. **Check if services are running:**
   ```bash
   # Check backend
   curl http://localhost:8000/health
   
   # Check frontend
   curl http://localhost/
   ```

2. **Check firewall:**
   ```bash
   sudo ufw allow 80
   sudo ufw allow 8000
   sudo ufw status
   ```

## Production Setup with Nginx

For production, use nginx as a reverse proxy:

1. **Install and configure nginx:**
   ```bash
   sudo cp nginx-http.conf /etc/nginx/sites-available/malware-detection
   sudo ln -s /etc/nginx/sites-available/malware-detection /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

2. **Update frontend to use nginx:**
   - Frontend will be served by nginx on port 80
   - API calls will be proxied to backend on port 8000

## Current Configuration

- **Server IP:** 206.189.138.156
- **Backend:** http://206.189.138.156:8000
- **Frontend:** http://206.189.138.156
- **API Endpoints:** http://206.189.138.156:8000/api/*
- **SSE Streams:** http://206.189.138.156:8000/notifications/stream