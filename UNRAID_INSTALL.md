# PDF Library Manager — Unraid Installation

Images are built automatically by GitHub Actions on every push to `main` and
published to GitHub Container Registry:

- `ghcr.io/jbowensii/pdf-lm:latest` — backend API + Celery worker (supervisor)
- `ghcr.io/jbowensii/pdf-lm-frontend:latest` — web UI (nginx, proxies /api to backend)

## One-time setup

### 1. Make the packages public (once, after the first CI build)

Go to <https://github.com/jbowensii?tab=packages>, open each package
(`pdf-lm` and `pdf-lm-frontend`) → **Package settings** → **Change visibility**
→ **Public**. Unraid can then pull without credentials.

*(Alternative: keep them private and run `docker login ghcr.io -u jbowensii`
on Unraid with a personal access token that has `read:packages`.)*

### 2. Create the data directories

```bash
mkdir -p /mnt/user/appdata/pdf-lm/{postgres,redis,logs}
mkdir -p /mnt/user/PDFGameVault
```

### 3. Create the stack in Compose Manager

1. **Add New Stack** → name it `pdf-lm`.
2. Paste the contents of [`docker-compose.prod.yml`](docker-compose.prod.yml)
   as the compose file.
3. In the stack's **.env** editor, set:

```env
DB_USER=pdf_user
DB_PASSWORD=<openssl rand -base64 24>
DB_NAME=pdf_library
SECRET_KEY=<openssl rand -hex 32>
WEB_PORT=3000
API_PORT=8000
```

4. **Compose Up**.

### 4. First run

1. Open `http://YOUR_UNRAID_IP:3000`
2. Register a user — **the first registered user automatically becomes admin**.
3. Drop PDFs into `/mnt/user/PDFGameVault`, then use the admin panel to scan
   the library.

Database tables are created automatically on first startup — no SQL scripts
or manual initialization needed.

## Updating

After any change is pushed to `main`, GitHub Actions rebuilds the images.
On Unraid, open the stack in Compose Manager and hit **Update Stack**
(equivalent to `docker compose pull && docker compose up -d`).

## Troubleshooting

```bash
docker logs pdf-lm-backend         # supervisor, API and worker output
docker exec pdf-lm-backend cat /app/logs/api.err      # API errors
docker exec pdf-lm-backend cat /app/logs/celery.err   # worker errors
curl http://localhost:8000/health  # API healthcheck (on the Unraid host)
```

| Symptom | Likely cause |
|---|---|
| `denied` when pulling images | Packages not public yet (step 1) |
| Frontend loads, API calls fail | Backend container not healthy — check its logs |
| Worker errors about Redis | Redis container not running |
