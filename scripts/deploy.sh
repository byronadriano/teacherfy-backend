#!/bin/bash
# scripts/deploy.sh - Deploy to Azure production environment

set -e

# Configuration
RESOURCE_GROUP="teacherfy-prod"
WEB_APP_NAME="teacherfy-web"
WORKER_APP_NAME="teacherfy-worker"
CONTAINER_REGISTRY="teacherfyregistry"
IMAGE_TAG=${1:-latest}

echo "🚀 Deploying Teacherfy Backend to Azure"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   Image Tag: $IMAGE_TAG"

# Check if Azure CLI is installed and logged in
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    exit 1
fi

if ! az account show &> /dev/null; then
    echo "❌ Not logged into Azure. Please run 'az login' first."
    exit 1
fi

# Build Docker images
echo "🔨 Building Docker images..."
docker build -f Dockerfile.web -t $CONTAINER_REGISTRY.azurecr.io/teacherfy-web:$IMAGE_TAG .
docker build -f Dockerfile.worker -t $CONTAINER_REGISTRY.azurecr.io/teacherfy-worker:$IMAGE_TAG .

# Push to Azure Container Registry
echo "📤 Pushing images to Azure Container Registry..."
az acr login --name $CONTAINER_REGISTRY
docker push $CONTAINER_REGISTRY.azurecr.io/teacherfy-web:$IMAGE_TAG
docker push $CONTAINER_REGISTRY.azurecr.io/teacherfy-worker:$IMAGE_TAG

# Deploy web app
echo "🌐 Deploying web application..."
az webapp config container set \
    --name $WEB_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --docker-custom-image-name $CONTAINER_REGISTRY.azurecr.io/teacherfy-web:$IMAGE_TAG

# Deploy worker (Container Instance)
echo "⚙️ Deploying worker containers..."
az container create \
    --resource-group $RESOURCE_GROUP \
    --name $WORKER_APP_NAME \
    --image $CONTAINER_REGISTRY.azurecr.io/teacherfy-worker:$IMAGE_TAG \
    --registry-login-server $CONTAINER_REGISTRY.azurecr.io \
    --registry-username $(az acr credential show --name $CONTAINER_REGISTRY --query "username" -o tsv) \
    --registry-password $(az acr credential show --name $CONTAINER_REGISTRY --query "passwords[0].value" -o tsv) \
    --environment-variables \
        REDIS_URL="$REDIS_URL" \
        POSTGRES_HOST="$POSTGRES_HOST" \
        POSTGRES_DB="$POSTGRES_DB" \
        POSTGRES_USER="$POSTGRES_USER" \
        POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
    --restart-policy Always \
    --cpu 2 \
    --memory 4

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Services:"
echo "   Web App: https://$WEB_APP_NAME.azurewebsites.net"
echo "   Worker:  Check Azure Portal for Container Instance status"
echo ""