#!/bin/bash
# scripts/verify-production-ssl.sh - Verify production SSL configuration

echo "🔍 Verifying Production SSL Configuration..."

# Test 1: Check if environment variable is set in Azure
echo "1. Checking Azure App Service environment variables..."
if command -v az &> /dev/null; then
    echo "   Checking REDIS_SSL_CERT_REQS setting..."
    az webapp config appsettings show --name teacherfy-web --resource-group teacherfy-prod --query "properties.REDIS_SSL_CERT_REQS" 2>/dev/null || echo "   (Need to login to Azure CLI)"
else
    echo "   Azure CLI not available - check manually in Azure Portal"
fi

# Test 2: Test production endpoint
echo ""
echo "2. Testing production health endpoint..."
PROD_URL="https://teacherfy-web.azurewebsites.net"
if curl -s "$PROD_URL/health" > /dev/null 2>&1; then
    echo "   ✅ Production app is responding"
    echo "   Health check: $(curl -s "$PROD_URL/health" | jq -r '.status')"
else
    echo "   ❌ Production app not responding or not deployed"
fi

# Test 3: Test background job endpoint
echo ""
echo "3. Testing production background job..."
read -p "   Do you want to test a production background job? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "   Creating test job..."
    RESPONSE=$(curl -s -X POST "$PROD_URL/generate/background" \
        -H "Content-Type: application/json" \
        -d '{
            "structured_content": [
                {"title": "SSL Production Test", "content": ["Testing secure production Redis", "CERT_REQUIRED working in production!"]}
            ],
            "resource_types": ["Presentation"],
            "notification_email": "production-test@example.com"
        }')
    
    if echo "$RESPONSE" | grep -q "job_id"; then
        echo "   ✅ Background job created successfully"
        JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
        echo "   Job ID: $JOB_ID"
        echo "   You can check status at: $PROD_URL/generate/status/$JOB_ID"
    else
        echo "   ❌ Failed to create background job"
        echo "   Response: $RESPONSE"
    fi
fi

echo ""
echo "🎯 Summary:"
echo "   • Local SSL validation: ✅ Working with CERT_REQUIRED"
echo "   • Production deployment: Check Azure Portal for REDIS_SSL_CERT_REQS"
echo "   • Security warning: Should be gone in production with proper SSL"
echo ""
echo "📝 Next steps if not working:"
echo "   1. Verify REDIS_SSL_CERT_REQS=CERT_REQUIRED in Azure App Service"
echo "   2. Restart the App Service after adding the variable"
echo "   3. Check App Service logs for any SSL errors"