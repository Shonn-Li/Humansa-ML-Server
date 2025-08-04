# Test Dashboard Architecture & System Overview

## 🏗️ System Architecture

The Test Management Dashboard is a comprehensive web-based system designed to manage, execute, and analyze tests for the YouWo AI ML Server. It consists of multiple components working together:

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Frontend UI        │────▶│  Backend API     │────▶│  ML Test Server │
│  Port: 3020         │     │  Port: 6002      │     │  Port: 6001     │
│  (React/HTML)       │     │  (FastAPI)       │     │  (Test Env)     │
└─────────────────────┘     └──────────────────┘     └─────────────────┘
         │                           │                         │
         │                           ▼                         │
         │                    ┌──────────────────┐            │
         │                    │  PostgreSQL      │            │
         └───────────────────▶│  test${digit}    │◀───────────┘
                              │  Port: 5454      │
                              └──────────────────┘
```

## 🔧 Components Overview

### 1. **Frontend (Port 3020)**
The dashboard has multiple frontend implementations:

- **React Frontend** (`test_dashboard/frontend/`)
  - Full-featured React 18 + TypeScript application
  - Uses Tailwind CSS for styling
  - Real-time updates via WebSocket
  - Dependencies: react-scripts, axios, lucide-react, @tanstack/react-query

- **Enhanced HTML** (`enhanced_dashboard.html`)
  - Single-file HTML dashboard with embedded JavaScript
  - Uses CDN for Tailwind CSS and Lucide icons
  - Lightweight alternative when npm dependencies fail

- **Simple HTML** (`test_dashboard_ui.html`)
  - Basic HTML interface created by verified scripts
  - Minimal dependencies, guaranteed to work

### 2. **Backend API (Port 6002)**
Multiple backend implementations exist:

- **Full Backend** (`test_dashboard/backend/main.py`)
  - Comprehensive FastAPI server
  - Expects complex module structure (api/, models/, etc.)
  - **Issue**: Missing required modules, causing import errors

- **Simple Backend** (`test_dashboard/backend/simple_main.py`)
  - Minimal FastAPI server with basic endpoints
  - Self-contained, no external module dependencies
  - **Recommended**: Works out of the box

- **Enhanced Backend** (`test_dashboard/backend/enhanced_main.py`)
  - Extended version with more features
  - WebSocket support for real-time updates
  - Test execution and monitoring capabilities

### 3. **Database (PostgreSQL)**
- **Test Database**: `test${digit}` (e.g., test4, test5)
- **Port**: 5454 (Docker container)
- **Container**: `youwoai_test_db`
- **Schema**: 11 tables for test management
- **Password**: 12931 (NOT 031203 as some docs suggest)

### 4. **ML Test Server (Port 6001)**
- Dedicated test instance of the ML server
- Launched via: `./run_HUMANSA_test_environment_v2_enhanced.sh`
- Environment: `ENVIRONMENT=test`
- Handles actual test execution

## 📁 Directory Structure

```
YouWoAI-ML-Server-1/
├── test_dashboard/
│   ├── backend/
│   │   ├── main.py              # Full backend (has issues)
│   │   ├── simple_main.py       # Simple working backend
│   │   ├── enhanced_main.py     # Enhanced backend
│   │   ├── core/                # Core modules
│   │   └── venv/                # Python virtual environment
│   │
│   └── frontend/
│       ├── src/
│       │   ├── App.tsx          # Main React component
│       │   ├── components/      # UI components
│       │   ├── services/        # API services
│       │   └── types/           # TypeScript types
│       ├── package.json         # npm dependencies
│       └── node_modules/        # (Often corrupted)
│
├── test_definitions/            # Standardized test JSON files
│   ├── converted/               # Converted test cases
│   └── test_schema.json         # Test format schema
│
├── Launch Scripts:
├── launch_test_dashboard.sh     # Original launch script
├── launch_dashboard_fixed.sh    # Fixed version (uses simple_main.py)
├── test_dashboard_verified.sh   # Verified working script
├── simple_dashboard.py          # All-in-one Python solution
├── enhanced_dashboard.html      # Standalone HTML dashboard
└── TEST_DASHBOARD_LAUNCH.md     # Launch documentation
```

## 🚀 Launch Methods

### Method 1: Verified Script (Most Reliable)
```bash
./test_dashboard_verified.sh
```
- Uses existing Python venv
- Launches simple_main.py backend
- Creates basic HTML frontend
- **Status**: ✅ Works

### Method 2: Simple Dashboard (Python Only)
```bash
./run_dashboard.sh
# or
python simple_dashboard.py
```
- Single Python file serving both frontend and backend
- No npm dependencies
- **Status**: ✅ Works

### Method 3: Enhanced HTML Dashboard
```bash
# Start backend
cd test_dashboard/backend
python simple_main.py

# Open enhanced_dashboard.html in browser
```
- Uses enhanced HTML file
- No build process required
- **Status**: ✅ Works

### Method 4: Full React Dashboard (Currently Broken)
```bash
./launch_test_dashboard.sh
```
- Full React frontend with all features
- **Status**: ❌ Fails due to:
  1. Backend import errors (missing api modules)
  2. Frontend npm dependency conflicts (ajv/webpack issues)

## 🔴 Current Issues

### 1. Backend Import Error
```
ModuleNotFoundError: No module named 'test_dashboard.backend.api'
```
**Cause**: main.py expects modules that don't exist
**Solution**: Use simple_main.py instead

### 2. Frontend Dependency Issues
```
Error: Cannot find module 'ajv/dist/compile/codegen'
Error: Cannot find module 'webpack'
```
**Cause**: Incomplete or corrupted node_modules
**Solution**: Clean reinstall or use HTML alternatives

### 3. Node.js Version Compatibility
- Using Node.js v22.13.1 (very recent)
- react-scripts 5.0.1 may have compatibility issues
- Consider downgrading to Node 18 LTS

## 🛠️ API Endpoints

The backend provides these endpoints:

- `GET /` - API info
- `GET /api/health` - System health check
- `GET /api/environments` - List ML servers (1-10)
- `GET /api/tests` - Get test catalog (847 tests)
- `GET /api/jobs` - Job management
- `GET /api/results` - Test results
- `GET /api/runs/{run_id}` - Specific run details
- `WS /ws` - WebSocket for real-time updates
- `GET /docs` - FastAPI automatic documentation

## 📊 Test Statistics

- **Total Tests**: 847 across 51 files
- **Categories**: 21 (appointment, medical, product, etc.)
- **Success Rate**: 43.5%
- **Top Categories**:
  - Appointment: 119 tests
  - Framework: 71 tests
  - Multi-turn: 67 tests
  - Product: 55 tests

## 🔧 Quick Fix Solutions

### Option 1: Use Working Script
```bash
./test_dashboard_verified.sh
```

### Option 2: Fix and Use Simple Backend
```bash
# Kill existing processes
lsof -ti:6002 | xargs kill -9 2>/dev/null

# Start simple backend
cd test_dashboard/backend
python simple_main.py &

# Open enhanced HTML in browser
open enhanced_dashboard.html
```

### Option 3: Full Fix (if needed)
```bash
# Fix backend: Edit launch scripts to use simple_main.py
sed -i '' 's/python3 main.py/python3 simple_main.py/g' launch_test_dashboard.sh

# Fix frontend: Use Node 18 and clean install
nvm use 18
cd test_dashboard/frontend
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

## 📝 Summary

The Test Dashboard is a sophisticated system with multiple implementation options. While the full React + complex backend setup has issues, there are several working alternatives:

1. **For immediate use**: Run `./test_dashboard_verified.sh`
2. **For simplicity**: Use `simple_dashboard.py`
3. **For features**: Use `enhanced_dashboard.html` with `simple_main.py`
4. **For full experience**: Fix the dependency issues and use the complete React app

The system is designed to manage 847+ tests across 21 categories, with real-time monitoring and comprehensive analytics. The core issue is that the original implementation expected a more complex structure than what exists, but the simplified versions work perfectly well for test management needs.