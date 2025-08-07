# CLAUDE.md - Humansa ML Server

## Project Overview
This is the Humansa ML Server, a specialized medical AI system that has been separated from the main YouWoAI repository for better separation of concerns.

## Recent Changes
- Moved from YouWoAI-ML-Server-1 to humansa-ml-server repository
- Fixed database schema issues with standardized test data
- Implemented multi-instance test dashboard with 4 ML server instances

## Database Schema Standards
All test instances use the following standardized schema:

### Key Tables
- `humansa_clinics` - Uses `clinic_code` as primary key (not `clinic_id`)
- `humansa_doctor` - Uses `doctor_code` as primary key (not `doctor_id`)
- `humansa_medical_service` - Medical services linked by `clinic_code`

### Column Standards
- Doctor references: Use `doctor_code` (not `doctor_id`)
- Clinic references: Use `clinic_code` (not `clinic_id`)
- All foreign keys must match these standards

### Test Data
Standardized test data includes:
- 11 clinics (H1-H5, CL001-CL003, CLINIC001-CLINIC003)
- 9 doctors (D1-D5, DOC001-DOC004)
- 25 medical services (SVC001-SVC025)

## Test Dashboard Configuration
- 4 ML server instances: ports 6011-6014
- 4 test databases: ports 5061-5064
- Dashboard backend: port 6002
- Dashboard frontend: port 3002

## Common Issues and Fixes

### Database Column Errors
If you see errors like "column d.doctor_id does not exist":
1. The code expects `doctor_code` not `doctor_id`
2. Check `/src/humansa/postgres/database.py` for SQL queries
3. Ensure all queries use the correct column names

### Test Execution
- Parallel workers should be based on available instances (4), not job configuration
- Each instance gets its own database to prevent contamination
- Tests should check for tool call errors vs agent response variations

## Running Tests
```bash
# Initialize instances
curl -X POST "http://localhost:6002/api/instances/initialize" -H "Content-Type: application/json" -d '{"num_instances": 4}'

# Run test suite
# Use the test dashboard to execute the 22 test cases
```

## Important Files
- `/test_dashboard/apply_standardized_test_data.sql` - Standardized test data
- `/test_dashboard/DATABASE_SCHEMA_FIXES.md` - Documentation of schema fixes
- `/src/humansa/postgres/database.py` - Main database queries (check for column names)
- `/src/humansa/v2/agents/appointment_agent.py` - Appointment booking logic
- `/src/humansa/v2/tools/db_medical_tools.py` - Medical service queries