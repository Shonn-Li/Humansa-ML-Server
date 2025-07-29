# HUMANSA TEST ENVIRONMENT - CRITICAL DOCUMENTATION

## ⚠️ IMPORTANT: This is a COMPLETELY ISOLATED Test Environment ⚠️

The Humansa test environment is a **DEDICATED, STATIC, and COMPLETELY INDEPENDENT** testing infrastructure specifically designed for Humansa AI agent testing.

## Key Characteristics

### 🔴 COMPLETE ISOLATION
- **Separate Docker Container**: Spins up its OWN PostgreSQL container
- **Separate ML Server**: Runs its OWN ML server instance
- **Independent Data**: Has its OWN test data that is STATIC and PREDICTABLE
- **No Production Impact**: NEVER touches production data or servers
- **Clean State**: RESETS to a known state on EVERY test run

### 🔴 FIXED PORTS (NEVER CHANGE THESE)
```bash
ML_SERVER_PORT=6001      # Humansa ML Server ALWAYS runs on 6001
DB_PORT=5454            # PostgreSQL ALWAYS runs on 5454
```

### 🔴 DATABASE CONFIGURATION
```bash
DB_NAME=test4           # Database name is ALWAYS test4
DB_USER=postgres        # User is ALWAYS postgres  
DB_PASSWORD=12931       # Password is ALWAYS 12931
DB_HOST=localhost       # Always localhost (Docker container)
```

## Test Data Structure

All test data is loaded from `test_environment/sql/` in this order:
1. `01_extensions.sql` - PostgreSQL extensions (pgvector, etc.)
2. `02_create_tables.sql` - Core tables
3. `03_test_data.sql` - General test data
4. `04_embeddings.sql` - Vector embeddings
5. `05_test_conversations.sql` - Conversation history
6. `06_humansa_test_data.sql` - Humansa-specific tables
7. `07_humansa_his_alignment.sql` - HIS API alignment
8. `08_appointment_management.sql` - Appointment tables
9. `humansa_test_doctors.sql` - Doctor test data

## Running Tests

### V2 Enhanced Test (40 Test Cases)
```bash
./run_humansa_v2_test_40_cases_enhanced.sh
```

### V2 Standard Test
```bash
./run_humansa_test_environment_v2_enhanced.sh
```

### V1 Test
```bash
./run_humansa_test_environment.sh
```

## What Happens During Test Execution

1. **Database Reset**: PostgreSQL container is reset to clean state
2. **SQL Scripts Run**: All test data is loaded fresh
3. **ML Server Starts**: Dedicated instance on port 6001
4. **Tests Execute**: Tests run against isolated environment
5. **Cleanup**: Server stops, but data persists for debugging

## Common Mistakes to Avoid

❌ **DO NOT** use port 5001 for Humansa tests - that's for general tests  
❌ **DO NOT** use port 5456 - that's a different test environment  
❌ **DO NOT** connect to production database  
❌ **DO NOT** modify test ports or credentials  

## Debugging

### Check if test database is running:
```bash
pg_isready -h localhost -p 5454 -U postgres
```

### Connect to test database:
```bash
PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4
```

### Check ML server health:
```bash
curl http://localhost:6001/api/debug/health
```

### View test logs:
```bash
# ML Server logs
tail -f server_enhanced.log

# Test results
ls test_results_v2_40cases_enhanced/
```

## Test Data Contents

The test environment includes:
- **15 test doctors** across different specialties
- **6 test clinics** in Beijing, Shanghai, Guangzhou, Shenzhen
- **180 schedule slots** for the next 7 days
- **25 medical services** with pricing
- **Test patients** with medical history
- **Appointment history** for testing continuity

## Environment Variables

When running tests, these are AUTOMATICALLY set:
```bash
export ENVIRONMENT=test
export DB_HOST=localhost
export DB_PORT=5454
export DB_USER=postgres
export DB_PASSWORD=12931
export DB_NAME=test4
export ML_SERVER_PORT=6001
export HUMANSA_ENHANCED_LOGGING=true
```

## Summary

🎯 **Remember**: The Humansa test environment is COMPLETELY ISOLATED and uses:
- ML Server: **Port 6001**
- PostgreSQL: **Port 5454**
- Database: **test4**
- Password: **12931**

This ensures consistent, reproducible testing without any impact on production systems.