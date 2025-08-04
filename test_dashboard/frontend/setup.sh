#!/bin/bash

# React Frontend Setup Script
# This script fixes Node.js version compatibility and dependency issues

set -e

echo "🔧 React Frontend Setup Script"
echo "==============================="

# Check if we're in the correct directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the frontend directory."
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if nvm is installed
if ! command_exists nvm; then
    echo "⚠️  NVM not found. Checking for Node.js version..."
    current_node_version=$(node --version 2>/dev/null || echo "none")
    
    if [[ "$current_node_version" == "none" ]]; then
        echo "❌ Node.js is not installed. Please install Node.js 18.20.4 or use NVM."
        echo "   Install NVM: https://github.com/nvm-sh/nvm#installing-and-updating"
        exit 1
    elif [[ "$current_node_version" =~ ^v18\. ]]; then
        echo "✅ Node.js version $current_node_version is compatible (Node 18.x)"
    else
        echo "⚠️  Current Node.js version: $current_node_version"
        echo "   Recommended: Node.js 18.20.4 (specified in .nvmrc)"
        echo "   You can continue, but you may encounter compatibility issues."
        read -p "   Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "   Install NVM to easily manage Node versions: https://github.com/nvm-sh/nvm"
            exit 1
        fi
    fi
else
    echo "📋 Using NVM to switch to Node.js version specified in .nvmrc..."
    
    # Load nvm
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    
    # Install and use the Node version from .nvmrc
    if [ -f ".nvmrc" ]; then
        echo "📥 Installing/using Node.js version from .nvmrc..."
        nvm install
        nvm use
    else
        echo "❌ .nvmrc file not found!"
        exit 1
    fi
fi

echo ""
echo "🧹 Cleaning up existing node_modules and lock files..."
rm -rf node_modules
rm -f package-lock.json

echo ""
echo "📦 Installing dependencies..."
echo "   This may take a few minutes..."

# Use npm ci for clean install with exact versions
if npm ci; then
    echo "✅ Dependencies installed successfully!"
else
    echo "⚠️  npm ci failed, trying npm install..."
    if npm install; then
        echo "✅ Dependencies installed successfully!"
    else
        echo "❌ Failed to install dependencies."
        echo ""
        echo "🔍 Troubleshooting steps:"
        echo "1. Make sure you're using Node.js 18.x"
        echo "2. Clear npm cache: npm cache clean --force"
        echo "3. Delete node_modules and package-lock.json, then try again"
        echo "4. Check for any global package conflicts"
        exit 1
    fi
fi

echo ""
echo "🧪 Running a quick test to verify the setup..."
if npm run build --silent >/dev/null 2>&1; then
    echo "✅ Build test passed!"
    rm -rf build  # Clean up test build
else
    echo "⚠️  Build test failed, but dependencies are installed."
    echo "   You may need to fix code issues before the app will start."
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Start the development server: npm start"
echo "   2. The app will run on http://localhost:3020"
echo "   3. If you encounter issues, check the troubleshooting guide"
echo ""
echo "💡 Tip: If you're using NVM, remember to run 'nvm use' in this directory"
echo "   before working on the project to ensure you're using the correct Node version."