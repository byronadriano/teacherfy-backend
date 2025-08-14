# 🚀 Background Jobs System

## New API Endpoints
- `POST /generate/background` - Start background job
- `GET /generate/status/{job_id}` - Check job status  
- `POST /generate/cancel/{job_id}` - Cancel job

## Required Azure Environment Variables
Set these in your Azure App Service Configuration:
```
REDIS_URL = [Your Azure Redis Cache connection string]
SMTP_SERVER = smtp.porkbun.com
SMTP_PORT = 587
SMTP_USE_TLS = true
SMTP_USERNAME = [Your email username]
SMTP_PASSWORD = [Your email password]
FROM_EMAIL = [Your from email address]
```

## What Users Get
- Instant job submission (no waiting)
- Email notifications when resources are ready
- Can close browser and get notified later

## Cost: ~$16/month (Azure Redis only)

## 🚨 Deployment Fix for Azure

If you get "503 Background job processing not available", run this in Azure SSH:

```bash
# 1. Test Celery installation
python test_celery.py

# 2. If failed, manually install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Restart the app
# (Use Azure portal restart button)
```

## Azure Startup Command
Set this as your startup command in Azure App Service:
```bash
bash deploy.sh gunicorn --bind=0.0.0.0:$PORT --workers=2 --timeout=120 app:app
```

## System Architecture
- **Celery**: Background task processing
- **Redis**: Message broker and result backend
- **SMTP**: Email notifications via Porkbun
- **Flask**: Main web application

Ready to deploy! 🚀