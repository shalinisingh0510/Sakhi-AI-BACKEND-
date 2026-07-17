# Sakhi AI Backend - Deployment Guide

## Prerequisites

- Python 3.12 or higher
- SQLite3
- Git
- A server or cloud hosting provider (AWS, GCP, Azure, or VPS)

## Environment Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Sakhi-AI-BACKEND-
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and configure it for production:

```bash
cp .env.example .env
```

Edit `.env` with production values:

```bash
# Application Settings
SAKHI_APP_NAME=Sakhi AI API
SAKHI_APP_VERSION=0.1.0
SAKHI_ENVIRONMENT=production
SAKHI_DEBUG=false

# CORS Settings (comma-separated list of allowed origins)
SAKHI_CORS_ORIGINS=https://your-frontend-domain.com

# Database Settings
SAKHI_DATABASE_PATH=/var/lib/sakhi-ai/production.sqlite3

# AI Settings
SAKHI_AI_PROVIDER_NAME=rule-based
SAKHI_CONVERSATION_HISTORY_LIMIT=8

# Security Settings (IMPORTANT: Generate a secure random key)
SAKHI_SECRET_KEY=your-32-byte-random-secret-key
SAKHI_ACCESS_TOKEN_MINUTES=60
SAKHI_REFRESH_TOKEN_DAYS=7

# Rate Limiting Settings
SAKHI_RATE_LIMIT_REQUESTS_PER_MINUTE=120
```

### 5. Generate Secure Secret Key

Generate a secure 32-byte random secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use the output as your `SAKHI_SECRET_KEY`.

## Database Setup

### 1. Create Database Directory

```bash
sudo mkdir -p /var/lib/sakhi-ai
sudo chown $USER:$USER /var/lib/sakhi-ai
```

### 2. Set Appropriate Permissions

```bash
chmod 700 /var/lib/sakhi-ai
```

## Running the Application

### Development Mode

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode with Gunicorn

Install Gunicorn:

```bash
pip install gunicorn
```

Run with Gunicorn:

```bash
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
```

### Using Systemd (Linux)

Create a systemd service file at `/etc/systemd/system/sakhi-ai.service`:

```ini
[Unit]
Description=Sakhi AI Backend API
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/sakhi-ai-backend
Environment="PATH=/var/www/sakhi-ai-backend/venv/bin"
ExecStart=/var/www/sakhi-ai-backend/venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /var/log/sakhi-ai/access.log \
    --error-logfile /var/log/sakhi-ai/error.log \
    --log-level info
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sakhi-ai
sudo systemctl start sakhi-ai
```

## Using Docker (Optional)

### 1. Create Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /var/lib/sakhi-ai

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### 2. Build and Run

```bash
docker build -t sakhi-ai-backend .
docker run -d \
    --name sakhi-ai \
    -p 8000:8000 \
    -v /var/lib/sakhi-ai:/var/lib/sakhi-ai \
    --env-file .env \
    sakhi-ai-backend
```

## Nginx Configuration (Optional)

Configure Nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

For HTTPS, use Certbot:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Security Considerations

1. **Secret Key**: Always use a strong, randomly generated secret key in production
2. **Database**: Ensure proper file permissions on the SQLite database
3. **CORS**: Only whitelist trusted frontend domains
4. **Rate Limiting**: Adjust rate limits based on your traffic patterns
5. **HTTPS**: Always use HTTPS in production
6. **Firewall**: Configure firewall to only allow necessary ports
7. **Updates**: Keep dependencies updated regularly

## Monitoring and Logging

### Application Logs

Logs are written to:
- Access logs: `/var/log/sakhi-ai/access.log`
- Error logs: `/var/log/sakhi-ai/error.log`

### Health Check

Monitor the health endpoint:

```bash
curl https://your-domain.com/api/v1/health
```

Expected response:

```json
{
    "status": "ok",
    "service": "Sakhi AI API",
    "version": "0.1.0"
}
```

## Backup Strategy

### Database Backup

Create a backup script:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/sakhi-ai"
DATE=$(date +%Y%m%d_%H%M%S)
cp /var/lib/sakhi-ai/production.sqlite3 $BACKUP_DIR/sakhi_ai_$DATE.sqlite3
# Keep only last 7 days of backups
find $BACKUP_DIR -name "sakhi_ai_*.sqlite3" -mtime +7 -delete
```

Add to cron for daily backups:

```bash
crontab -e
# Add: 0 2 * * * /path/to/backup-script.sh
```

## Troubleshooting

### Service Won't Start

Check logs:
```bash
sudo journalctl -u sakhi-ai -f
```

### Database Permission Issues

```bash
sudo chown www-data:www-data /var/lib/sakhi-ai/production.sqlite3
sudo chmod 640 /var/lib/sakhi-ai/production.sqlite3
```

### Port Already in Use

```bash
sudo lsof -i :8000
sudo kill -9 <PID>
```

## Performance Tuning

### Adjust Worker Count

Based on CPU cores:
```bash
# Formula: (2 * CPU cores) + 1
gunicorn app.main:app --workers 5 ...
```

### Database Optimization

For high traffic, consider:
- Migrating to PostgreSQL
- Adding connection pooling
- Implementing read replicas

## Scaling

### Horizontal Scaling

- Load balance across multiple instances
- Use shared storage for database
- Implement session management

### Vertical Scaling

- Increase server resources
- Optimize database queries
- Add caching layer (Redis)

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Secure secret key generated
- [ ] Database directory created with proper permissions
- [ ] SSL/TLS certificate installed
- [ ] Firewall configured
- [ ] Monitoring setup
- [ ] Backup strategy implemented
- [ ] Health endpoint accessible
- [ ] Rate limiting configured
- [ ] CORS origins whitelisted
- [ ] Dependencies updated
- [ ] Application tested in staging environment

## Support

For issues or questions:
- Check logs: `/var/log/sakhi-ai/error.log`
- Review this documentation
- Check GitHub issues
