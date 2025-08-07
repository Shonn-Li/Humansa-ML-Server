# Frontend Troubleshooting Guide

This guide helps resolve common issues with the React frontend setup.

## Quick Fix - Automated Setup

**Recommended approach:** Run the setup script that automatically fixes most issues:

```bash
# On macOS/Linux
./setup.sh

# On Windows
setup.bat
```

## Manual Steps

If you prefer to fix issues manually or the script doesn't work:

### 1. Node.js Version Issues

**Problem:** react-scripts 5.0.1 is incompatible with Node.js v22+

**Solution:**
```bash
# Install Node.js 18.20.4 (recommended)
# Using NVM (recommended):
nvm install 18.20.4
nvm use 18.20.4

# Verify version
node --version  # Should show v18.20.4
```

### 2. Missing Dependencies (webpack/ajv)

**Problem:** `Cannot find module 'ajv/dist/compile/codegen'` or similar webpack errors

**Solution:** The package.json has been updated with explicit versions and overrides:
```bash
# Clean install
rm -rf node_modules package-lock.json
npm install
```

### 3. Dependency Conflicts

**Problem:** Version conflicts between packages

**Solutions:**
```bash
# Clear npm cache
npm cache clean --force

# Remove and reinstall
rm -rf node_modules package-lock.json
npm install

# Force resolution (if needed)
npm install --force
```

### 4. Development Server Issues

**Problem:** Server won't start or crashes

**Solutions:**
```bash
# Check port availability (app uses port 3020)
lsof -i :3020  # macOS/Linux
netstat -ano | findstr :3020  # Windows

# Kill process if needed
kill -9 <PID>  # macOS/Linux

# Start with debugging
npm start --verbose
```

### 5. Build Issues

**Problem:** Build fails with TypeScript or webpack errors

**Solutions:**
```bash
# Check TypeScript config
npx tsc --noEmit

# Clear TypeScript cache
rm -rf .tscache

# Rebuild
npm run build
```

## Environment Verification

Run these commands to verify your environment:

```bash
# Check versions
node --version          # Should be v18.x.x
npm --version          # Should be 9.x.x or 10.x.x
npx react-scripts --version  # Should be 5.0.1

# Check if app builds
npm run build

# Check if app starts
npm start
```

## Common Error Messages

### "digital envelope routines::unsupported"
- **Cause:** Node.js 17+ incompatibility with older webpack
- **Fix:** Use Node.js 18 LTS (specified in .nvmrc)

### "Cannot find module 'ajv/dist/compile/codegen'"
- **Cause:** ajv version incompatibility
- **Fix:** Explicit ajv version in package.json (done automatically)

### "webpack < 5 used to include polyfills"
- **Cause:** Missing webpack 5 configuration
- **Fix:** Updated webpack version and configuration

### "Error: Cannot find module 'webpack'"
- **Cause:** Missing webpack dependency
- **Fix:** Added webpack to devDependencies

## Project Structure

```
frontend/
├── .nvmrc                 # Node.js version specification
├── package.json           # Updated with fixed dependencies
├── setup.sh              # Automated setup script (Unix)
├── setup.bat             # Automated setup script (Windows)
├── TROUBLESHOOTING.md    # This file
├── src/                  # Source code
├── public/               # Static assets
└── node_modules/         # Dependencies (auto-generated)
```

## Getting Help

If you're still experiencing issues:

1. Check the Node.js version: `node --version`
2. Clear everything and start fresh:
   ```bash
   rm -rf node_modules package-lock.json
   ./setup.sh  # or setup.bat on Windows
   ```
3. Check for global package conflicts:
   ```bash
   npm list -g --depth=0
   ```
4. Try running with verbose logging:
   ```bash
   npm start --verbose
   ```

## Prevention

To avoid future issues:
- Always use Node.js 18.x for this project (check .nvmrc)
- Don't install global packages that might conflict
- Use `npm ci` instead of `npm install` when possible
- Keep dependencies updated gradually, not all at once