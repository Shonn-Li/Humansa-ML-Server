@echo off
setlocal enabledelayedexpansion

:: React Frontend Setup Script (Windows)
:: This script fixes Node.js version compatibility and dependency issues

echo 🔧 React Frontend Setup Script (Windows)
echo =======================================

:: Check if we're in the correct directory
if not exist "package.json" (
    echo ❌ Error: package.json not found. Please run this script from the frontend directory.
    pause
    exit /b 1
)

:: Check Node.js version
echo 📋 Checking Node.js version...
for /f "tokens=*" %%i in ('node --version 2^>nul') do set node_version=%%i

if "!node_version!"=="" (
    echo ❌ Node.js is not installed. Please install Node.js 18.20.4.
    echo    Download from: https://nodejs.org/
    pause
    exit /b 1
)

echo Current Node.js version: !node_version!

:: Check if it's Node 18.x
echo !node_version! | findstr /r "^v18\." >nul
if !errorlevel! equ 0 (
    echo ✅ Node.js version is compatible (Node 18.x)
) else (
    echo ⚠️  Recommended: Node.js 18.20.4
    echo    You can continue, but you may encounter compatibility issues.
    set /p continue="Continue anyway? (y/N): "
    if /i not "!continue!"=="y" (
        echo    Please install Node.js 18.x from: https://nodejs.org/
        pause
        exit /b 1
    )
)

echo.
echo 🧹 Cleaning up existing node_modules and lock files...
if exist "node_modules" rmdir /s /q "node_modules"
if exist "package-lock.json" del "package-lock.json"

echo.
echo 📦 Installing dependencies...
echo    This may take a few minutes...

:: Try npm ci first, then npm install
npm ci >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ Dependencies installed successfully!
) else (
    echo ⚠️  npm ci failed, trying npm install...
    npm install
    if !errorlevel! equ 0 (
        echo ✅ Dependencies installed successfully!
    ) else (
        echo ❌ Failed to install dependencies.
        echo.
        echo 🔍 Troubleshooting steps:
        echo 1. Make sure you're using Node.js 18.x
        echo 2. Clear npm cache: npm cache clean --force
        echo 3. Delete node_modules and package-lock.json, then try again
        echo 4. Check for any global package conflicts
        pause
        exit /b 1
    )
)

echo.
echo 🧪 Running a quick test to verify the setup...
npm run build --silent >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ Build test passed!
    if exist "build" rmdir /s /q "build"
) else (
    echo ⚠️  Build test failed, but dependencies are installed.
    echo    You may need to fix code issues before the app will start.
)

echo.
echo 🎉 Setup complete!
echo.
echo 📝 Next steps:
echo    1. Start the development server: npm start
echo    2. The app will run on http://localhost:3020
echo    3. If you encounter issues, check the troubleshooting guide
echo.
echo 💡 Tip: Make sure to always use Node.js 18.x for this project
echo    to avoid compatibility issues.

pause