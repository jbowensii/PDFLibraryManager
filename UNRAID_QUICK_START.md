# PDF Library Manager - Unraid Quick Start (5 Minutes)

## TL;DR - Get Running Fast

### Prerequisites
- Unraid with Docker enabled
- 2GB+ RAM available
- Network access to your Unraid server

### 5-Minute Setup

#### 1. SSH into Unraid and Create Directories
```bash
mkdir -p /mnt/user/appdata/pdf-lm/{postgres,redis,uploads,logs}
mkdir -p /mnt/user/PDFGameVault
```

#### 2. Generate Passwords
```bash
# Database password (copy the output)
openssl rand -base64 32

# Secret key (copy the output)
openssl rand -hex 32
```

#### 3. Create /mnt/user/appdata/pdf-lm/.env
```bash
DB_USER=pdf_user
DB_PASSWORD=<PASTE_PASSWORD_FROM_STEP_2>
DB_NAME=pdf_library
SECRET_KEY=<PASTE_SECRET_KEY_FROM_STEP_2>
GITHUB_USERNAME=jbowensii
IMAGE_TAG=latest
API_PORT=8000
WEB_PORT=3000
API_URL=http://192.168.X.X:8000/api/v1
```
(Replace `192.168.X.X` with your Unraid server's IP)

#### 4. Create docker-compose.prod.yml in /mnt/user/appdata/pdf-lm/

Copy the full content from the project's `docker-compose.prod.yml` file, or use:

```bash
# Clone or download the file from GitHub
curl -o docker-compose.prod.yml https://raw.githubusercontent.com/jbowensii/PDFLibraryManager/main/docker-compose.prod.yml
```

#### 5. Deploy
```bash
cd /mnt/user/appdata/pdf-lm
source .env
docker-compose -f docker-compose.prod.yml up -d
```

#### 6. Verify Running
```bash
docker-compose -f docker-compose.prod.yml ps
# Look for: All containers showing "Up" status
```

#### 7. Access Web UI
Open your browser to: **http://192.168.X.X:3000**
- Click "Register"
- Create your admin user
- Login

#### 8. Add PDFs
```bash
# Copy PDFs to library
cp /path/to/your/*.pdf /mnt/user/PDFGameVault/

# Scan in web UI: Admin → "Scan Library"
```

## Common Commands

### View Logs
```bash
# Combined logs
docker logs pdf-lm-backend

# API logs only
docker exec pdf-lm-backend tail -f /app/logs/api.log

# Celery worker logs
docker exec pdf-lm-backend tail -f /app/logs/celery.log
```

### Restart Services
```bash
# Restart everything
docker-compose -f docker-compose.prod.yml restart

# Restart just the API/Celery
docker-compose -f docker-compose.prod.yml restart pdf-lm
```

### Check Worker Status
```bash
docker exec pdf-lm-backend supervisorctl status
# Should show both 'api' and 'celery' as RUNNING
```

### Stop/Remove Everything
```bash
docker-compose -f docker-compose.prod.yml down

# Keep data, remove containers only
docker-compose -f docker-compose.prod.yml down -v
# WARNING: -v removes volumes (data will be deleted)
```

## Port Reference

| Service | Port | URL |
|---------|------|-----|
| API | 8000 | http://IP:8000/health |
| API Docs | 8000 | http://IP:8000/docs |
| Web UI | 3000 | http://IP:3000 |
| Database | 5432 | Internal only |
| Cache | 6379 | Internal only |

## Troubleshooting

### "Connection refused" when opening web UI
- Wait 30 seconds for containers to fully start
- Check `docker-compose ps` to verify all are running

### "Database is not ready"
- Check postgres logs: `docker logs pdf-lm-postgres`
- Wait for healthcheck to show "healthy"

### Celery not processing tasks
- Check worker: `docker exec pdf-lm-backend supervisorctl status celery`
- Restart: `docker exec pdf-lm-backend supervisorctl restart celery`

### Port already in use
- Change API_PORT or WEB_PORT in .env file
- Restart: `docker-compose -f docker-compose.prod.yml restart`

### Out of disk space
- Clear old logs: `rm /mnt/user/appdata/pdf-lm/logs/*.log`
- Check database size: `docker exec pdf-lm-postgres du -sh /var/lib/postgresql/data`

## Next Steps

- Read full guide: `UNRAID_INSTALL.md` for advanced setup
- Configure users in Admin panel
- Set up backups (see UNRAID_INSTALL.md)
- Invite family members to use the library

## Help

- API Documentation: http://YOUR_IP:8000/docs
- GitHub Issues: https://github.com/jbowensii/PDFLibraryManager/issues
- Detailed Guide: `UNRAID_INSTALL.md` in project root

---

**Ready to use in ~5-10 minutes depending on download speeds**
