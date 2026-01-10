#!/bin/bash

# Start Frontend Server Script
# This script builds and serves the React frontend

echo "Starting Malware Detection Gateway Frontend..."

# Navigate to frontend directory
cd Frontend

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed"
    exit 1
fi

# Install dependencies
echo "Installing Node.js dependencies..."
npm install

# Build the frontend for production
echo "Building frontend for production..."
npm run build

# Install a simple HTTP server if not already installed
if ! command -v serve &> /dev/null; then
    echo "Installing serve package..."
    npm install -g serve
fi

# Serve the built frontend
echo "Starting frontend server on http://0.0.0.0:80"
serve -s dist -l 80