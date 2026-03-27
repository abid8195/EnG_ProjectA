# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p backend/uploads backend/datasets

# Set environment variables
ENV FLASK_APP=backend/app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Create startup script
RUN echo '#!/bin/bash\ncd /app\ngunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 backend.app:app' > start.sh && \
    chmod +x start.sh

# Run the application
CMD ["./start.sh"]