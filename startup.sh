#!/bin/bash

# Azure App Service startup script for QML DataFlow Studio
echo "Starting QML DataFlow Studio on Azure App Service..."

# Set environment variables
export PYTHONPATH="/home/site/wwwroot:$PYTHONPATH"
export FLASK_APP="backend/app.py"
export FLASK_ENV="production"

# Create necessary directories
mkdir -p /home/site/wwwroot/backend/uploads
mkdir -p /home/site/wwwroot/backend/datasets

# Copy datasets if they don't exist
if [ ! -f "/home/site/wwwroot/backend/datasets/diabetes.csv" ]; then
    echo "Copying datasets..."
    cp /home/site/wwwroot/backend/datasets/* /home/site/wwwroot/backend/datasets/ 2>/dev/null || true
fi

# Start the application
echo "Starting Flask application..."
cd /home/site/wwwroot
gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 backend.app:app