#!/bin/bash

# Start Backend Server Script
# This script starts the FastAPI backend server

echo "Starting Malware Detection Gateway Backend..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed"
    exit 1
fi

# Install requirements if not already installed
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Create necessary directories
mkdir -p logs
mkdir -p data
mkdir -p model

# Set environment variables for production
export ENVIRONMENT=production
export DEBUG=false
export LOG_LEVEL=info
export HOST=0.0.0.0
export PORT=8000

# Start the backend server
echo "Starting backend server on http://0.0.0.0:8000"
python3 app.py