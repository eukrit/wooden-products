# Leka Salesheet server — Python/Flask with static content
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server
COPY server.py .

# Copy static content (everything else) into ./static
RUN mkdir -p static
COPY index.html            static/index.html
COPY wpc-fence             static/wpc-fence

ENV PORT=8080
EXPOSE 8080

# Cloud Run respects $PORT. 1 worker is enough for static-ish service; threaded for concurrency.
CMD exec gunicorn \
    --bind 0.0.0.0:${PORT} \
    --workers 2 \
    --threads 8 \
    --timeout 30 \
    --access-logfile - \
    --error-logfile - \
    server:app
