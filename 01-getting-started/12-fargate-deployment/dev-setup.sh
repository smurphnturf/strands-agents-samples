#!/bin/bash

# Local Development Setup Script
# This script helps set up and run the restaurant assistant app locally using Docker

set -e

echo "🚀 Restaurant Assistant Local Development Setup"
echo "=============================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Python 3 is available for credential extraction
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "⚠️  Python not found. Manual .env setup will be required."
    PYTHON_CMD=""
fi

# Check if .env file exists and try to auto-populate it
if [ ! -f .env ]; then
    echo "⚠️  No .env file found."
    
    if [ -n "$PYTHON_CMD" ]; then
        echo "🔍 Attempting to extract AWS credentials from CLI cache..."
        if $PYTHON_CMD extract-aws-creds.py --bucket strandsagentfargatestack-strandsagentagentbucket34-ak8knpf0jinc 2>/dev/null; then
            echo "✅ AWS credentials extracted successfully!"
        else
            echo "⚠️  Could not extract AWS credentials automatically."
            echo "📝 Creating .env from template..."
            cp .env.example .env
            echo ""
            echo "Please either:"
            echo "  1. Run 'awsume team' (or similar) and then run this script again"
            echo "  2. Manually edit .env file with your AWS credentials and bucket name"
            echo ""
            read -p "Press Enter to continue with manual setup or Ctrl+C to exit..."
        fi
    else
        echo "📝 Creating .env from template..."
        cp .env.example .env
        echo "📝 Please edit .env file with your AWS credentials and bucket name"
        echo "   Then run this script again."
        exit 1
    fi
fi

# Validate that required environment variables are set
if grep -q "your-agent-bucket-name\|your-access-key\|your-secret-key" .env 2>/dev/null; then
    echo "⚠️  .env file still contains placeholder values."
    if [ -n "$PYTHON_CMD" ]; then
        echo "🔄 Attempting to refresh AWS credentials..."
        if $PYTHON_CMD extract-aws-creds.py --bucket strandsagentfargatestack-strandsagentagentbucket34-ak8knpf0jinc 2>/dev/null; then
            echo "✅ AWS credentials refreshed successfully!"
        else
            echo "❌ Could not refresh credentials. Please check:"
            echo "   1. Run 'awsume team' to refresh your AWS session"
            echo "   2. Manually update .env file with valid credentials"
            exit 1
        fi
    else
        echo "❌ Please update .env file with valid AWS credentials and bucket name"
        exit 1
    fi
fi

# Build the development image
echo "🔨 Building development Docker image..."
docker build -f docker/Dockerfile -t restaurant-assistant-dev ./docker

echo "✅ Development image built successfully!"
echo ""
echo "🎯 You can now run the application using:"
echo "   docker compose -f docker-compose.dev.yml up"
echo ""
echo "📋 Available commands:"
echo "   Start:    docker compose -f docker-compose.dev.yml up"
echo "   Start (background): docker compose -f docker-compose.dev.yml up -d"
echo "   Stop:     docker compose -f docker-compose.dev.yml down"
echo "   Logs:     docker compose -f docker-compose.dev.yml logs -f"
echo "   Rebuild:  docker compose -f docker-compose.dev.yml up --build"
echo ""
echo "🌐 The app will be available at: http://localhost:8000"
echo "📋 Health check: http://localhost:8000/health"
echo "📋 API docs: http://localhost:8000/docs"
echo ""
echo "💡 Code changes in docker/app/ will automatically reload the server!"
