# Humansa Test Environment Guide

## Quick Start

### 1. Run Simple Test (3 cases)
```bash
./run_simple_humansa_test.sh
```
- Tests 3 essential scenarios
- Outputs to markdown file
- Takes ~1 minute

### 2. Run Comprehensive Test (20 cases)
```bash
./run_humansa_test_environment.sh
```
- Tests all 20 scenarios
- Detailed output with traces
- Takes ~5-10 minutes

## Utility Scripts

### Check Server Status
```bash
./check_server_status.sh
```
Shows:
- Port 6001 and 5001 status
- Running Python processes
- Server health check

### Kill Port 6001
```bash
./kill_port_6001.sh
```
Use when you get "Address already in use" errors.

### Load Test Data
```bash
./load_test_data.sh
```
Loads sample doctors, clinics, and services into database.

## Common Issues

### "Address already in use"
```bash
# Kill all processes on port 6001
./kill_port_6001.sh

# Then run test again
./run_simple_humansa_test.sh
```

### Empty tool responses
```bash
# Load test data first
./load_test_data.sh

# Check database connection in .env
cat .env | grep DB_
```

### Server not starting
```bash
# Check status
./check_server_status.sh

# Check logs
tail -50 simple_test_server.log
tail -50 test_server.log
```

## Test Output

### Terminal Output
- Real-time test progress
- Pass/fail status
- Response times

### Markdown Files
- `humansa_test_output_*.md` - Detailed test results
- Includes agent traces
- Tool calls and responses
- Formatted tables

## Environment Variables

Required in `.env`:
```
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=your_database
OPENAI_API_KEY=your_api_key
```

## Architecture Diagrams

- `HUMANSA_V2_FLOW_DIAGRAM.md` - Detailed flow (30+ components)
- `HUMANSA_V2_SIMPLE_FLOW.md` - Simplified flow (7 components)

## Test Data

The test data includes:
- 4 Doctors (王医生, 李医生, 张医生, 刘医生)
- 3 Clinics (Beijing, Shenzhen, Guangzhou)
- 4 Medical services (肝功能检查, 核磁共振, etc.)

## Tips

1. Always run `./kill_port_6001.sh` if previous test crashed
2. Check markdown output files for detailed analysis
3. Use simple test for quick validation
4. Use comprehensive test for full coverage