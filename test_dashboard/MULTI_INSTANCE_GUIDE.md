# Multi-Instance ML Server Testing - Quick Start Guide

## Overview

The test dashboard now includes integrated multi-instance support, allowing you to run tests in parallel with isolated ML server instances. Each instance has its own database, eliminating log contamination and providing true parallel execution.

## Default Configuration

- **Multi-Instance Mode**: Enabled
- **Auto-Start**: Disabled (to avoid conflicts on first launch)
- **Default Instances**: 4
- **Ports Used**:
  - Dashboard Backend: 6002
  - Dashboard Frontend: 3020
  - ML Servers: 6001, 6003, 6004, 6005 (skips 6002)
  - Databases: 5451, 5452, 5453, 5454

## Quick Start

### 1. Launch Dashboard

```bash
cd test_dashboard
./launch_dashboard.sh
```

This will:
- Start the backend on port 6002
- Start the frontend on port 3020
- Check settings for multi-instance configuration
- Display current configuration

### 2. Start Multi-Instance Infrastructure (Manual)

After the dashboard is running:

```bash
# In a new terminal, start database containers
cd test_environment
./start_multi_instance.sh

# Initialize ML server instances via API
curl -X POST http://localhost:6002/api/instances/initialize?num_instances=4

# Check instance status
curl http://localhost:6002/api/instances/status | jq
```

### 3. Enable Auto-Start (Optional)

To have instances start automatically on next launch:

```bash
# Update settings to enable auto-start
curl -X PUT http://localhost:6002/api/settings/multi-instance \
  -H 'Content-Type: application/json' \
  -d '{
    "enabled": true,
    "default_instances": 4,
    "auto_start": true
  }'
```

## Creating Jobs with Multi-Instance

### Default Behavior

By default, jobs use the dashboard settings:

```json
{
  "name": "My Test Job",
  "tests": [...],
  "config": {
    "max_parallel_workers": 4
    // use_multi_instance: inherits from dashboard settings
  }
}
```

### Override Multi-Instance Settings

Force multi-instance mode for a specific job:

```json
{
  "config": {
    "use_multi_instance": true,
    "max_parallel_workers": 4
  }
}
```

Force single-instance mode:

```json
{
  "config": {
    "use_multi_instance": false
  }
}
```

## API Reference

### Settings Management

```bash
# Get all settings
curl http://localhost:6002/api/settings | jq

# Update multi-instance settings
curl -X PUT http://localhost:6002/api/settings/multi-instance \
  -H 'Content-Type: application/json' \
  -d '{
    "enabled": true,
    "default_instances": 4,
    "auto_start": false,
    "max_workers_per_job": 4
  }'

# Apply settings (adjusts running instances)
curl -X POST http://localhost:6002/api/settings/multi-instance/apply
```

### Instance Management

```bash
# Check instance status
curl http://localhost:6002/api/instances/status | jq

# Initialize instances
curl -X POST http://localhost:6002/api/instances/initialize?num_instances=4

# Health check all instances
curl -X POST http://localhost:6002/api/instances/health-check

# Shutdown all instances
curl -X POST http://localhost:6002/api/instances/shutdown
```

## Troubleshooting

### Port Conflicts

- The system automatically skips digit 2 to avoid conflict with dashboard backend (port 6002)
- If you see "Port already in use" errors, check:
  ```bash
  lsof -i :6001  # Check what's using the port
  ```

### Database Connection Issues

- Ensure Docker is running
- Start database containers:
  ```bash
  cd test_environment
  ./start_multi_instance.sh
  ```
- Test connection:
  ```bash
  PGPASSWORD=youwo123 psql -h localhost -p 5451 -U youwo -d youwoai
  ```

### Instance Startup Failures

- Check the dashboard backend logs:
  ```bash
  tail -f test_dashboard/backend/backend.log
  ```
- Check instance-specific logs:
  ```bash
  tail -f /tmp/ml_server_instance_1.log
  ```

## Performance Tips

1. **Start Small**: Begin with 2-3 instances and increase based on system resources
2. **Monitor Resources**: Use `docker stats` to monitor database containers
3. **Adjust Workers**: Set `max_parallel_workers` to match available instances

## Example Workflow

```bash
# 1. Start dashboard
cd test_dashboard
./launch_dashboard.sh

# 2. In another terminal, start databases
cd test_environment
./start_multi_instance.sh

# 3. Initialize 4 instances
curl -X POST http://localhost:6002/api/instances/initialize?num_instances=4

# 4. Create and run a job
curl -X POST http://localhost:6002/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Parallel Test Run",
    "tests": [{"test_id": "HUM_001"}, {"test_id": "HUM_002"}],
    "config": {
      "max_parallel_workers": 4,
      "use_multi_instance": true
    }
  }'

# 5. Execute the job
curl -X POST http://localhost:6002/api/jobs/{job_id}/execute \
  -H 'Content-Type: application/json' \
  -d '{"environment_id": 1}'
```

## Settings Persistence

Settings are stored in `backend/dashboard_settings.json` and persist across restarts. To reset to defaults:

```bash
rm test_dashboard/backend/dashboard_settings.json
```