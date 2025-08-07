# Test Management Dashboard - Launch Instructions

## Quick Start (One Command)

```bash
./launch_test_dashboard.sh
```

This will automatically:
- Install all dependencies (if needed)
- Start the backend API on port 6002
- Start the frontend UI on port 3020
- Open your browser to http://localhost:3020

## What the Launch Script Does

1. **Checks Dependencies**
   - Ensures Python 3 and Node.js are installed
   - Creates virtual environment for Python
   - Installs all npm packages

2. **Starts Backend API (Port 6002)**
   - FastAPI server with WebSocket support
   - Connects to test database (test5 by default)
   - Provides REST API endpoints
   - Real-time updates via WebSocket

3. **Starts Frontend UI (Port 3020)**
   - React TypeScript application
   - Tailwind CSS for styling
   - Dark mode support
   - Real-time dashboard updates

## Manual Launch (Alternative)

If you prefer to launch manually:

### Backend:
```bash
cd test_dashboard/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
ML_DIGIT=5 python3 main.py
```

### Frontend:
```bash
cd test_dashboard/frontend
npm install
PORT=3020 npm start
```

## Access Points

- **Frontend Dashboard**: http://localhost:3020
- **Backend API**: http://localhost:6002
- **API Documentation**: http://localhost:6002/docs
- **WebSocket**: ws://localhost:6002/ws

## Environment Variables

- `ML_DIGIT`: Which ML server to connect to (default: 5)
  - Determines database: test${ML_DIGIT}
  - ML server port: 5000 + ${ML_DIGIT}

## Features Available

### Dashboard Overview
- System health monitoring
- Test statistics (847 total tests)
- Environment selector (ML Servers 1-10)
- Real-time connection status

### Test Management
- Browse test catalog by category
- Create and manage test jobs
- Batch execution with parallel support
- Real-time execution monitoring

### Results Analytics
- Test results with drill-down
- Performance trends and charts
- Failure analysis with insights
- Export capabilities (CSV, JSON, PDF)

### Real-time Monitoring
- Live test execution tracking
- Log streaming
- Performance metrics
- WebSocket notifications

## Troubleshooting

### Port Already in Use
The script automatically kills processes on ports 3020 and 6002. If issues persist:
```bash
lsof -ti:3020 | xargs kill -9
lsof -ti:6002 | xargs kill -9
```

### Missing Dependencies
- **Node.js**: Download from https://nodejs.org/
- **Python 3**: Usually pre-installed on macOS/Linux
- **PostgreSQL**: Required for database connection

### Database Connection
Ensure PostgreSQL is running and the test database exists:
```bash
psql -U postgres -c "CREATE DATABASE test5;"
```

### Frontend Build Issues
If the frontend fails to start:
```bash
cd test_dashboard/frontend
rm -rf node_modules package-lock.json
npm install
PORT=3020 npm start
```

## Stop Services

Press `Ctrl+C` in the terminal running the launch script to stop all services.

## Development Mode

The dashboard runs in development mode by default with:
- Hot reloading for frontend changes
- Auto-restart for backend changes
- Detailed error messages
- Debug logging enabled

## Next Steps

1. Launch the dashboard: `./launch_test_dashboard.sh`
2. Navigate to http://localhost:3020
3. Select your ML server environment
4. Start creating test jobs and running tests!

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Frontend       │────▶│  Backend API     │────▶│  ML Server      │
│  Port: 3020     │     │  Port: 6002      │     │  Port: 5000+n   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                           │
                               ▼                           ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  PostgreSQL      │     │  Test Env       │
                        │  test${digit}    │     │  Port: 6001     │
                        └──────────────────┘     └─────────────────┘
```

The dashboard provides a complete test management solution with real-time monitoring, comprehensive analytics, and seamless integration with your ML infrastructure.