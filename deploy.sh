#!/bin/bash
# Deployment script for Render

echo "🚀 Starting deployment process..."

# Install dependencies
echo "📦 Installing dependencies..."
pip install -U pip

# Install CPU-only PyTorch first
echo "🔧 Installing CPU-only PyTorch..."
pip install --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple torch==2.9.0 torchvision==0.24.0

# Install other requirements
echo "📋 Installing other requirements..."
pip install -r requirements.txt

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "🗄️ Running migrations..."
python manage.py migrate

echo "✅ Deployment complete!"
