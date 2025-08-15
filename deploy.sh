#!/bin/bash
# deploy.sh - Azure App Service deployment script

echo "🚀 Starting Azure deployment..."

# Install dependencies explicitly
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Verify critical dependencies
echo "🔍 Verifying Celery installation..."
python -c "import celery; print(f'✅ Celery {celery.__version__} is available')" || {
    echo "❌ Celery installation failed"
    exit 1
}

echo "🔍 Verifying Redis installation..."
python -c "import redis; print(f'✅ Redis {redis.__version__} is available')" || {
    echo "❌ Redis installation failed"  
    exit 1
}

echo "🔍 Testing Celery configuration..."
python scripts/test_celery.py || {
    echo "⚠️ Celery configuration test failed, but continuing..."
}

echo "✅ Deployment preparation complete!"

# Start the application
echo "🌟 Starting application..."
exec "$@"