# Packet Inspection Transformer - VM Setup Guide

This guide provides complete instructions for deploying the Packet Inspection Transformer malware detection platform on a fresh Ubuntu VM.

## Prerequisites

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 20 GB | 50+ GB SSD |
| Network | Public IP | Static public IP |

### Required Access

- SSH access to the VM
- Sudo/root privileges
- Domain name (optional, for SSL)

---

## Quick Start

### Step 1: Clone and Prepare

```bash
# SSH into your VM
ssh user@<VM_PUBLIC_IP>

# Clone the repository
git clone https://github.com/yourusername/PacketInspectionTransformerV3.git
cd PacketInspectionTransformerV3

# Navigate to deploy directory
cd deploy

# Make scripts executable
chmod +x *.sh
```

### Step 2: Run Full Setup (Auto-SSL)

```bash
sudo ./menu.sh
```

Select option **1) Full Setup** from the menu.

During setup, you will be prompted for:
- **Domain name** (optional): Enter your domain for automatic HTTPS/SSL with Let's Encrypt
- Leave blank to use HTTP only

### Step 3: Upload Model File

```bash
# From your local machine
scp finetuned_best_model.pth user@<VM_PUBLIC_IP>:/opt/packet-inspection-transformer/model/

# Or if model is already on the server
sudo cp /path/to/finetuned_best_model.pth /opt/packet-inspection-transformer/model/
```

### Step 4: Start Services

```bash
sudo ./menu.sh
```

Select option **2) Run Services**.

### Step 5: Access Dashboard

Open your browser and navigate to:
```
# With SSL (if domain provided)
https://<VM_PUBLIC_IP>

# Without SSL (HTTP only)
http://<VM_PUBLIC_IP>
```

---

## Automatic SSL/HTTPS

The setup script automatically configures Let's Encrypt SSL certificates when a domain is provided:

1. **Prompt for domain** during `setup.sh` execution
2. **Verify DNS** points to your VM's IP
3. **Obtain certificate** from Let's Encrypt
4. **Configure nginx** with HTTPS
5. **Setup auto-renewal** (certificates renew automatically)

### SSL Options

| Option | Command | Result |
|--------|---------|--------|
| Auto-SSL with domain | `DOMAIN=example.com sudo ./setup.sh` | HTTPS automatically configured |
| Interactive SSL | Run `setup.sh` and enter domain when prompted | HTTPS configured |
| HTTP only | Run `setup.sh` and press Enter without domain | HTTP only (no SSL) |
| Manual SSL | Run `sudo ./setup-ssl.sh` later | Add SSL anytime |

### SSL Commands

```bash
# Automatic SSL setup (non-interactive)
sudo DOMAIN=yourdomain.com ./setup.sh

# Interactive SSL setup
sudo ./setup-ssl.sh

# Manual certbot
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## Manual Setup (Step-by-Step)

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Python and Dependencies

```bash
sudo apt install -y python3 python3-venv python3-pip curl wget git
```

### 3. Install Node.js 20.x

```bash
# Install NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -

# Install Node.js
sudo apt install -y nodejs

# Verify installation
node --version  # Should show v20.x.x
npm --version   # Should show 10.x.x
```

### 4. Install Nginx

```bash
sudo apt install -y nginx

# Enable and start nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 5. Install Certbot (for SSL)

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 6. Create Project Directory

```bash
sudo mkdir -p /opt/packet-inspection-transformer/{model,logs,dashboard}
```

### 7. Setup Python Virtual Environment

```bash
cd /opt/packet-inspection-transformer
sudo python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r /path/to/requirements.txt
deactivate
```

### 8. Build Frontend

```bash
cd /path/to/PacketInspectionTransformerV3/Frontend
sudo npm ci
sudo npm run build
sudo mv dist/* /opt/packet-inspection-transformer/dashboard/dist/
```

### 9. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/packet-inspection-transformer
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name _;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    gzip on;
    gzip_types text/plain text/css application/javascript application/json;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    location / {
        root /opt/packet-inspection-transformer/dashboard/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
}
```

Enable the site:

```bash
sudo ln -sf /etc/nginx/sites-available/packet-inspection-transformer /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 10. Start Backend

```bash
cd /opt/packet-inspection-transformer
source venv/bin/activate
nohup uvicorn app:app --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &
```

---

## Automatic SSL/HTTPS

SSL/HTTPS is now **automatically configured** during the main setup if you provide a domain name.

### During Setup (Recommended)

```bash
sudo ./menu.sh
# Select "1) Full Setup"
# Enter your domain name when prompted
```

### Non-Interactive Setup

```bash
# Set domain and run setup
sudo DOMAIN=yourdomain.com ./setup.sh
```

### Manual SSL Setup (Optional)

If you skipped SSL during initial setup, run:

```bash
sudo ./setup-ssl.sh
```

Or use certbot directly:

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### SSL Prerequisites

- Domain name with A record pointing to VM's public IP
- Port 80 (and 443) open in firewall
- For auto-renewal: port 80 must remain accessible

---

## Management Commands

### Using the Menu

```bash
cd /opt/packet-inspection-transformer/deploy
sudo ./menu.sh
```

Menu options:
1. **Full Setup** - Install all dependencies
2. **Run Services** - Start backend and nginx
3. **Restart Services** - Restart all services
4. **Clean All** - Remove all installed components
5. **Exit** - Exit the menu

### Manual Commands

```bash
# Start backend
cd /opt/packet-inspection-transformer
source venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000 &

# Stop backend
pkill -f "uvicorn app:app"

# Restart nginx
sudo systemctl restart nginx

# Check nginx status
sudo systemctl status nginx

# View logs
tail -f /opt/packet-inspection-transformer/logs/uvicorn.log
```

---

## File Structure

```
/opt/packet-inspection-transformer/
├── model/                    # ML model files
│   └── finetuned_best_model.pth
├── logs/                     # Application logs
│   ├── uvicorn.log
│   └── uvicorn.error.log
├── dashboard/                # Frontend build
│   └── dist/
│       ├── index.html
│       ├── assets/
│       └── ...
├── venv/                     # Python virtual environment
└── deploy/                   # Deployment scripts (on source)
```

---

## Troubleshooting

### Backend Not Starting

```bash
# Check if port 8000 is in use
sudo lsof -i :8000

# Check logs
cat /opt/packet-inspection-transformer/logs/uvicorn.log

# Check virtual environment
source /opt/packet-inspection-transformer/venv/bin/activate
pip list
```

### Nginx Errors

```bash
# Test nginx configuration
sudo nginx -t

# Check nginx status
sudo systemctl status nginx

# View nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Frontend Not Loading

```bash
# Check if build exists
ls -la /opt/packet-inspection-transformer/dashboard/dist/

# Check nginx configuration
sudo cat /etc/nginx/sites-available/packet-inspection-transformer
```

### Model Not Found

```bash
# Verify model file
ls -la /opt/packet-inspection-transformer/model/

# Check model path in configuration
cat /opt/packet-inspection-transformer/config/model_config.py
```

---

## Firewall Configuration

### UFW (Uncomplicated Firewall)

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

### Cloud Firewall (AWS, GCP, Azure)

Ensure the following inbound rules are configured:
- SSH (22/tcp) - Your IP
- HTTP (80/tcp) - Anywhere (0.0.0.0/0)
- HTTPS (443/tcp) - Anywhere (0.0.0.0/0)

---

## Security Best Practices

1. **Disable root SSH login**
2. **Use SSH key authentication**
3. **Configure fail2ban**
4. **Enable automatic security updates**
5. **Use SSL in production**
6. **Keep credentials secure**
7. **Regularly update the system**

```bash
# Install fail2ban
sudo apt install -y fail2ban

# Enable automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## Model Management

### Upload Model via SCP

```bash
# From your local machine
scp finetuned_best_model.pth user@<VM_IP>:/tmp/

# On the VM
sudo mv /tmp/finetuned_best_model.pth /opt/packet-inspection-transformer/model/
sudo chmod 644 /opt/packet-inspection-transformer/model/finetuned_best_model.pth
```

### Reload Model

```bash
# Restart the backend to load new model
sudo pkill -f "uvicorn app:app"
cd /opt/packet-inspection-transformer
source venv/bin/activate
nohup uvicorn app:app --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &
```

---

## Updating the Application

### 1. Pull Latest Code

```bash
cd /path/to/PacketInspectionTransformerV3
git pull origin main
```

### 2. Rebuild Frontend

```bash
cd Frontend
npm ci
npm run build
sudo mv dist/* /opt/packet-inspection-transformer/dashboard/dist/
```

### 3. Update Python Dependencies

```bash
source /opt/packet-inspection-transformer/venv/bin/activate
pip install -r requirements.txt --upgrade
deactivate
```

### 4. Restart Services

```bash
sudo ./restart.sh
```

---

## Monitoring

### Check Service Status

```bash
# Check if backend is running
ps aux | grep uvicorn

# Check nginx status
sudo systemctl status nginx

# Check ports in use
sudo netstat -tulpn | grep -E '(8000|80|443)'
```

### View Logs

```bash
# Backend logs
tail -f /opt/packet-inspection-transformer/logs/uvicorn.log

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Health Check

```bash
# Check backend health
curl http://localhost:8000/health

# Check nginx health
curl http://localhost/health
```

---

## Support

For issues or questions:

1. Check the [ troubleshooting section](#troubleshooting)
2. Review application logs: `/opt/packet-inspection-transformer/logs/`
3. Review nginx logs: `/var/log/nginx/`
4. Open an issue on GitHub

---

## License

This project is licensed under the MIT License.