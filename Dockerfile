FROM python:3.11-slim

# HF Spaces requires a non-root user with uid 1000
RUN useradd -m -u 1000 appuser

WORKDIR /app

# System deps needed by numpy/scipy (Qiskit dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY --chown=appuser:appuser . .

# Create runtime directories with correct ownership
RUN mkdir -p uploads models logs && \
    chown -R appuser:appuser uploads models logs datasets

USER appuser

# HF Spaces free tier uses port 7860
ENV PORT=7860
EXPOSE 7860

CMD ["waitress-serve", "--host=0.0.0.0", "--port=7860", "--threads=4", "app:app"]
