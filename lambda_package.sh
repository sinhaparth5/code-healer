#!/bin/bash
set -e

echo "🚀 Starting Lambda packaging process..."

# Clean up previous builds
echo "🧹 Cleaning up old builds..."
rm -rf deployment
rm -f lambda_package.zip

# Create deployment directory
echo "📁 Creating deployment directory..."
mkdir -p deployment

# Copy source code
echo "📋 Copying source code..."
cp -r src/* deployment/

# Navigate to deployment directory
cd deployment

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "❌ ERROR: requirements.txt not found!"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
echo "   This may take a few minutes..."
pip3 install -r requirements.txt \
    --target . \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.13 \
    --only-binary=:all: \
    --upgrade

# Create zip file
echo "🗜️  Creating ZIP package..."
zip -r9 ../lambda_package.zip . \
    -x "*.git*" \
    -x "*.pyc" \
    -x "*__pycache__*" \
    -x "*.DS_Store" \
    -x "*.gitignore" \
    2>/dev/null

cd ..

# Get file size
SIZE=$(du -h lambda_package.zip | cut -f1)
echo ""
echo "✅ Package created successfully!"
echo "📦 File: lambda_package.zip"
echo "📏 Size: $SIZE"
echo ""

# Check if size is too large for direct upload
SIZE_BYTES=$(stat -f%z lambda_package.zip 2>/dev/null || stat -c%s lambda_package.zip 2>/dev/null)
if [ $SIZE_BYTES -gt 52428800 ]; then
    echo "⚠️  WARNING: Package is larger than 50MB!"
    echo "   You'll need to upload to S3 first."
    echo ""
    echo "   Run this command:"
    echo "   aws s3 cp lambda_package.zip s3://your-bucket/lambda_package.zip"
else
    echo "✨ Package size is good for direct upload to Lambda!"
fi

echo ""
echo "🎯 Next steps:"
echo "   1. Upload to Lambda console OR"
echo "   2. Run: aws lambda update-function-code --function-name codehealer-handler --zip-file fileb://lambda_package.zip"