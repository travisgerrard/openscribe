#!/bin/bash

# Citrix Transcriber Build Script
# This script packages the application for distribution

set -e  # Exit on any error

echo "🚀 Starting Citrix Transcriber Build Process..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[BUILD]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    print_error "main.py not found. Please run this script from the project root directory."
    exit 1
fi

if [ ! -f "package.json" ]; then
    print_error "package.json not found. Please run this script from the project root directory."
    exit 1
fi

# Clean previous builds
print_status "Cleaning previous builds..."
rm -rf dist/
rm -rf build/
mkdir -p dist/

# Check Python virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "No virtual environment detected. Activating whisper_env..."
    if [ -d "whisper_env" ]; then
        source whisper_env/bin/activate
        print_success "Activated whisper_env"
    else
        print_error "whisper_env not found. Please create and activate your Python virtual environment."
        exit 1
    fi
else
    print_success "Using virtual environment: $VIRTUAL_ENV"
fi

# Install/update Python dependencies
print_status "Checking Python dependencies..."
pip install --upgrade pyinstaller
print_success "Python dependencies ready"

# Install/update Node dependencies
print_status "Checking Node.js dependencies..."
npm install
print_success "Node.js dependencies ready"

# Build Python backend
print_status "Building Python backend with PyInstaller..."
pyinstaller build_backend.spec --clean --noconfirm

if [ ! -f "dist/CitrixTranscriberBackend.app/Contents/MacOS/citrix-transcriber-backend" ]; then
    print_error "Python backend build failed!"
    exit 1
fi

print_success "Python backend built successfully"

# Test Python backend
print_status "Testing Python backend..."
# Quick test to see if the executable starts
timeout 5 ./dist/CitrixTranscriberBackend.app/Contents/MacOS/citrix-transcriber-backend --help || true
print_success "Python backend test completed"

# Build Electron application
print_status "Building Electron application..."
npm run build:electron

# Check if build was successful
if [ -d "dist/mac" ]; then
    print_success "macOS build completed successfully!"
    
    # Show what was built
    print_status "Build artifacts:"
    ls -la dist/
    
    if [ -f "dist/Citrix Transcriber-*.dmg" ]; then
        DMG_FILE=$(ls dist/Citrix\ Transcriber-*.dmg | head -1)
        DMG_SIZE=$(du -h "$DMG_FILE" | cut -f1)
        print_success "DMG installer created: $DMG_FILE ($DMG_SIZE)"
    fi
    
    if [ -d "dist/mac/Citrix Transcriber.app" ]; then
        APP_SIZE=$(du -sh "dist/mac/Citrix Transcriber.app" | cut -f1)
        print_success "App bundle created: Citrix Transcriber.app ($APP_SIZE)"
    fi
    
    echo ""
    echo "🎉 Build completed successfully!"
    echo ""
    echo "📦 Distribution files:"
    echo "   • DMG installer: dist/Citrix Transcriber-*.dmg"
    echo "   • App bundle: dist/mac/Citrix Transcriber.app"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Test the DMG installer on a clean macOS system"
    echo "   2. Share the DMG file with your wife"
    echo "   3. She can simply drag the app to Applications and run it!"
    echo ""
    
else
    print_error "Build failed! Check the output above for errors."
    exit 1
fi 