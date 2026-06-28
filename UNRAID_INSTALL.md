# PDF Library Manager - Unraid Installation Guide

A self-hosted PDF library server with OCR and metadata enrichment capabilities. This guide walks you through deploying the PDF Library Manager on Unraid using Docker.

## Architecture Overview

The consolidated deployment consists of 3 Docker containers:
- **postgres** — PostgreSQL database for storing metadata and job status
- **redis** — Redis cache and message broker for Celery task queue
- **pdf-lm** — Single container running both FastAPI API server and Celery worker (via supervisor)
- **frontend** — React web UI (optional, can be served from backend)

## Prerequisites

- Unraid with Docker support enabled
- At least 2GB RAM available for the PDF Library Manager container
- At least 1GB disk space for database and application data
- Network access to your Unraid server
- A GitHub account (to pull container images from GitHub Container Registry)

## Step 1: Create Storage Directories

SSH into your Unraid server and create the required directories:

```bash
mkdir -p /mnt/user/appdata/pdf-lm/{postgres,redis,uploads,logs}
mkdir -p /mnt/user/PDFGameVault
```

**Unraid Permissions:**
- Set proper permissions if needed:
  ```bash
  chmod 755 /mnt/user/appdata/pdf-lm
  chmod 755 /mnt/user/PDFGameVault
  ```

## Step 2: Create Environment Configuration

Create `/mnt/user/appdata/pdf-lm/.env` with the following content:

```bash
# Database Configuration
DB_USER=pdf_user
DB_PASSWORD=<GENERATE_STRONG_PASSWORD_HERE>
DB_NAME=pdf_library

# Application Security
SECRET_KEY=<GENERATE_WITH_COMMAND_BELOW>

# Docker Image Configuration
GITHUB_USERNAME=jbowensii
IMAGE_TAG=latest

# API and Web UI Ports
API_PORT=8000
WEB_PORT=3000

# Frontend API URL (adjust to your Unraid IP)
API_URL=http://YOUR_UNRAID_IP:8000/api/v1
```

### Generate Secure Passwords and Keys

Run these commands to generate secure values:

**Database Password:**
```bash
openssl rand -base64 32
```

**Secret Key:**
```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
# Or without Python:
openssl rand -hex 32
```

Save these values and update the `.env` file.

## Step 3: Create docker-compose.prod.yml

Create `/mnt/user/appdata/pdf-lm/docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    container_name: pdf-lm-postgres
    environment:
      POSTGRES_DB: ${DB_NAME:-pdf_library}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - /mnt/user/appdata/pdf-lm/postgres:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: pdf-lm-redis
    volumes:
      - /mnt/user/appdata/pdf-lm/redis:/data
    restart: unless-stopped

  pdf-lm:
    image: ghcr.io/${GITHUB_USERNAME}/pdf-lm:${IMAGE_TAG:-latest}
    container_name: pdf-lm-backend
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME:-pdf_library}
      REDIS_URL: redis://redis:6379
      DEBUG: "false"
      LOG_LEVEL: INFO
      SECRET_KEY: ${SECRET_KEY}
    ports:
      - "${API_PORT:-8000}:8000"
    volumes:
      - /mnt/user/PDFGameVault:/library
      - /mnt/user/appdata/pdf-lm/uploads:/app/uploads
      - /mnt/user/appdata/pdf-lm/logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: ghcr.io/${GITHUB_USERNAME}/pdf-lm-frontend:${IMAGE_TAG:-latest}
    container_name: pdf-lm-frontend
    environment:
      REACT_APP_API_URL: ${API_URL:-http://localhost:8000/api/v1}
    ports:
      - "${WEB_PORT:-3000}:3000"
    depends_on:
      - pdf-lm
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
  redis_data:

networks:
  default:
    name: pdf-lm-prod
```

## Step 4: Deploy Using Docker Compose

SSH into your Unraid server and navigate to the app directory:

```bash
cd /mnt/user/appdata/pdf-lm
```

Load environment variables and start the services:

```bash
# Make sure .env file is in the current directory
source .env

# Pull the latest images
docker-compose -f docker-compose.prod.yml pull

# Start the services
docker-compose -f docker-compose.prod.yml up -d
```

Verify all containers are running:

```bash
docker-compose -f docker-compose.prod.yml ps
```

Expected output:
```
NAME                 COMMAND                  SERVICE      STATUS
pdf-lm-postgres      "docker-entrypoint..."   postgres     Up
pdf-lm-redis         "redis-server /etc..."   redis        Up
pdf-lm-backend       "/usr/bin/superviso..."  pdf-lm       Up (healthy)
pdf-lm-frontend      "/docker-entrypoint..."  frontend     Up (healthy)
```

## Step 5: Initial Setup

1. **Open the Web UI:**
   Navigate to `http://YOUR_UNRAID_IP:3000` in your browser

2. **Register First User:**
   - Click "Register" or "Sign Up"
   - Create your admin user account
   - The first user automatically becomes an admin

3. **Login:**
   - Enter your credentials to access the dashboard

4. **Configure Library Path:**
   - Go to Admin Settings (gear icon)
   - Verify library path is `/library` (mapped from `/mnt/user/PDFGameVault`)

5. **Scan Library:**
   - Click "Scan Library" in the Admin panel
   - System will discover and index PDFs

## Step 6: Add PDFs to Your Library

Place PDF files in the library directory:

```bash
cp /path/to/pdf/files/*.pdf /mnt/user/PDFGameVault/
```

Then trigger a library scan in the web UI:
- Admin Panel → "Scan Library" → Wait for indexing to complete

## Step 7: Monitor and Manage

### View Logs

Check the combined supervisor logs:
```bash
docker logs pdf-lm-backend
```

Check individual services:
```bash
# API logs
docker exec pdf-lm-backend tail -f /app/logs/api.log

# Celery worker logs
docker exec pdf-lm-backend tail -f /app/logs/celery.log

# Supervisor logs
docker exec pdf-lm-backend tail -f /app/logs/supervisord.log
```

### Verify Database

Check that the database is initialized:
```bash
docker exec pdf-lm-postgres psql -U pdf_user -d pdf_library -c "\dt"
```

### Restart Services

```bash
# Restart all services
docker-compose -f docker-compose.prod.yml restart

# Restart only the API/Celery container
docker-compose -f docker-compose.prod.yml restart pdf-lm
```

## Troubleshooting

### Container Won't Start

Check logs for errors:
```bash
docker-compose -f docker-compose.prod.yml logs pdf-lm
```

Common issues:
- **Database not ready**: Wait 10-15 seconds and retry
- **Port already in use**: Change API_PORT or WEB_PORT in .env
- **Image not found**: Ensure GITHUB_USERNAME is correct and you have internet access

### Database Connection Error

Verify PostgreSQL is healthy:
```bash
docker-compose -f docker-compose.prod.yml ps postgres
# Should show "healthy" status

# Or manually test:
docker exec pdf-lm-postgres pg_isready -U pdf_user
```

### Celery Worker Not Processing Tasks

Check worker status:
```bash
docker exec pdf-lm-backend supervisorctl status celery
```

Restart the worker:
```bash
docker exec pdf-lm-backend supervisorctl restart celery
```

### Redis Connection Issues

Verify Redis is running:
```bash
docker exec pdf-lm-redis redis-cli PING
# Should return: PONG
```

### High Memory Usage

Monitor container resource usage:
```bash
docker stats pdf-lm-backend
```

If OCR is consuming too much memory:
1. Reduce CELERY_CONCURRENCY in the container (defaults to 2)
2. Edit docker-compose.prod.yml or environment variables

## Advanced Configuration

### Enable GPU Acceleration (Optional)

If your Unraid server has an Nvidia GPU, enable CUDA for faster OCR:

1. Install nvidia-docker runtime on Unraid
2. Update docker-compose.prod.yml:
   ```yaml
   pdf-lm:
     runtime: nvidia
     environment:
       NVIDIA_VISIBLE_DEVICES: all
   ```

### Backup and Restore

**Backup Database:**
```bash
docker exec pdf-lm-postgres pg_dump -U pdf_user pdf_library > /mnt/user/appdata/pdf-lm/backup_$(date +%Y%m%d).sql
```

**Restore Database:**
```bash
docker exec -i pdf-lm-postgres psql -U pdf_user pdf_library < /mnt/user/appdata/pdf-lm/backup_20240628.sql
```

**Backup Everything:**
```bash
tar czf /mnt/user/appdata/pdf-lm/backup_$(date +%Y%m%d).tar.gz /mnt/user/appdata/pdf-lm/
```

### Scale Celery Workers (If Needed)

To run multiple Celery worker processes within the same container, edit the supervisor config inside the container or mount a custom supervisord.conf.

## API Documentation

Once running, access the interactive API documentation:
- **Swagger UI:** `http://YOUR_UNRAID_IP:8000/docs`
- **ReDoc:** `http://YOUR_UNRAID_IP:8000/redoc`

## Support and Updates

- **Project Repository:** https://github.com/jbowensii/PDFLibraryManager
- **Issues:** GitHub Issues tracker
- **Updates:** Pull latest images with `docker-compose pull`

## Next Steps

1. Create user accounts for family members in the Admin panel
2. Configure sharing settings if desired
3. Set up scheduled backups
4. Monitor logs for any issues during initial use
5. Consider enabling HTTPS with a reverse proxy (nginx) for external access
