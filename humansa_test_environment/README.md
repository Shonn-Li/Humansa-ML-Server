# HUMANSA Test Environment

Test environment configuration for the HUMANSA medical AI system.

## Overview

This test environment provides:
- 🏥 Medical consultation system with AI agents
- 👨‍⚕️ 10 doctors across various specialties
- 🏢 5 clinics in different Singapore regions
- 📅 Appointment booking system
- 💊 Patient medical records and medication tracking
- 🏥 Health screening packages
- 🏦 Insurance provider integration

## Quick Start

```bash
# Setup the entire environment
./setup.sh

# Test the connection
python tests/test_connection.py

# Reset data (keep containers running)
./scripts/reset_data.sh

# Clean up everything
./cleanup.sh
```

## Directory Structure

```
humansa_test_environment/
├── docker/                 # Docker configuration
│   └── docker-compose.yml  # PostgreSQL container setup
├── sql/                    # Database schemas
│   └── setup_humansa_test_db.sql
├── scripts/                # Utility scripts
│   ├── populate_humansa_test_data.py
│   └── reset_data.sh
├── tests/                  # Test files
│   └── test_connection.py
├── docs/                   # Documentation
├── setup.sh               # Main setup script
├── cleanup.sh             # Cleanup script
└── README.md              # This file
```

## Database Configuration

- **Host**: localhost
- **Port**: 5454 (shared test container)
- **Database**: test4 (HUMANSA-specific database)
- **User**: postgres
- **Password**: 12931
- **Container**: youwoai_test_db

## Test Data

### Users (5 test patients)
- John Tan - Software Engineer, healthy
- Mary Lim - Teacher with diabetes & hypertension
- Robert Lee - Retiree with heart conditions
- Sarah Wong - Marketing Manager with allergies
- David Ng - Business Owner with asthma

### Doctors (10 specialists)
- General Practice (2)
- Cardiology (2)
- Endocrinology (1)
- Dermatology (1)
- Pediatrics (1)
- Orthopedics (1)
- Psychiatry (1)
- Ophthalmology (1)

### Clinics (5 locations)
- Raffles Medical - Central
- Mount Elizabeth Medical Centre - Orchard
- Parkway East Hospital - East Coast
- Gleneagles Medical Centre - Tanglin
- Thomson Medical Centre - Novena

### Features
- 30 days of appointment slots
- Dynamic slot availability
- Medical history tracking
- Medication management
- Insurance verification
- Health package recommendations

## Running Tests

### Test Database Connection
```bash
cd humansa_test_environment
python tests/test_connection.py
```

### Run HUMANSA V2 Tests
```bash
# From project root
source youwo-ml-venv/bin/activate
export DB_PORT=5454 DB_NAME=test4 DB_PASSWORD=12931
python test_HUMANSA_v2_comprehensive.py
```

### Start ML Server with HUMANSA Database
```bash
# From project root
source youwo-ml-venv/bin/activate
export DB_PORT=5454 DB_NAME=test4 DB_PASSWORD=12931
python -m src.main --port 6001
```

## API Endpoints

When the ML server is running with Humansa database:

- `/v1-humansa/chat/completions` - Medical consultation with tool calling
- `/v1-humansa/o3-demo` - O3 demo endpoint with advanced reasoning

## Maintenance

### Reset Data Only
```bash
./scripts/reset_data.sh
```
This keeps the Docker container running but drops and recreates all tables with fresh test data.

### Complete Cleanup
```bash
./cleanup.sh
```
This removes:
- Docker containers
- Docker volumes
- Test artifacts
- Database data

### Update Test Data
Edit `src/humansa/v2/test_data.py` to modify:
- Doctors
- Clinics
- Health packages
- Insurance providers

Then run `./scripts/reset_data.sh` to apply changes.

## Shared Test Infrastructure

This environment uses shared test infrastructure:
- Shared PostgreSQL container on port 5454
- HUMANSA uses database `test4`
- YouWoAI general tests use database `youwoai_test`
- Both share the same container but have separate databases

## Troubleshooting

### Container Not Running
If the test database is not running:
1. Check for existing containers: `docker ps | grep youwoai_test_db`
2. Start the container: `cd test_environment && docker-compose up -d`
3. Verify connection: `PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -c 'SELECT 1;'`

### Import Errors
If you see import errors when running scripts:
1. Ensure you're in the project root
2. Activate virtual environment: `source youwo-ml-venv/bin/activate`
3. Install dependencies: `pip install asyncpg psycopg2-binary`

### Database Connection Failed
1. Check Docker is running: `docker ps`
2. Verify container is up: `docker ps | grep humansa_test_postgres`
3. Check logs: `docker logs humansa_test_postgres`

## Related Documentation

- Main test environment: `/test_environment/README.md`
- Humansa V2 implementation: `/src/humansa/v2/README.md`
- Test environments guide: `/TEST_ENVIRONMENTS_GUIDE.md`