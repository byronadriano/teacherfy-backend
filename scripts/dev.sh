#!/bin/bash
# scripts/dev.sh - Start local development environment

set -e

echo "🚀 Starting Teacherfy Backend Development Environment"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    echo "   cp .env.example .env"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Build and start services
echo "🔨 Building Docker containers..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
docker-compose ps

echo ""
echo "✅ Development environment is ready!"
echo ""
echo "🌐 Services:"
echo "   Web App:     http://localhost:5000"
echo "   Flower UI:   http://localhost:5555"
echo "   Redis:       localhost:6379"
echo ""
echo "📋 Useful commands:"
echo "   View logs:        docker-compose logs -f"
echo "   Stop services:    docker-compose down"
echo "   Restart:          docker-compose restart"
echo "   Shell access:     docker-compose exec web bash"
echo ""