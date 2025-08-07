# Database Initialization Scripts

This directory contains all SQL scripts needed to initialize different environments for the Humansa ML Server and Test Dashboard.

## Directory Structure

```
database/init/
├── test_management/     # Test dashboard management database (port 5432)
│   ├── 01_schema.sql    # Create test_management schema and tables
│   └── 02_indexes.sql   # Create indexes and constraints
│
├── humansa_app/         # Humansa application tables
│   ├── 01_extensions.sql    # PostgreSQL extensions (pgvector, etc.)
│   ├── 02_core_tables.sql   # Core Humansa tables (patients, appointments, etc.)
│   ├── 03_mem0_tables.sql   # Memory system tables
│   └── 04_sample_data.sql   # Sample test data
│
└── test_instances/      # Test instance initialization (ports 5061-5064)
    └── init_instance.sql    # Combined script for test instances
```

## Usage

### For Test Dashboard (Main Database - Port 5432)

```bash
# Initialize test_management schema
PGPASSWORD=youwo123 psql -h localhost -p 5432 -U postgres -d test5 \
  -f database/init/test_management/01_schema.sql
```

### For Test Instances (Ports 5061-5064)

```bash
# Initialize each test instance
for port in 5061 5062 5063 5064; do
  PGPASSWORD=youwo123 psql -h localhost -p $port -U youwo -d youwoai \
    -f database/init/test_instances/init_instance.sql
done
```

### For Development Environment

```bash
# Initialize development database with Humansa tables
PGPASSWORD=youwo123 psql -h localhost -p 5432 -U postgres -d test5 \
  -f database/init/humansa_app/01_extensions.sql \
  -f database/init/humansa_app/02_core_tables.sql \
  -f database/init/humansa_app/03_mem0_tables.sql
```

## Environment Variables

The scripts expect these environment variables or defaults:

- `DB_HOST`: Database host (default: localhost)
- `DB_PORT`: Database port (varies by use case)
- `DB_NAME`: Database name (test5 for management, youwoai for instances)
- `DB_USER`: Database user (postgres for management, youwo for instances)
- `DB_PASSWORD`: Database password (youwo123)

## Docker Usage

For Docker containers, mount this directory and run initialization:

```yaml
volumes:
  - ./database/init:/docker-entrypoint-initdb.d
```

## Notes

1. **Test Management Schema**: Always applied to the main database (port 5432, database test${DIGIT})
2. **Test Instances**: Each runs in its own container (ports 5061-5064, database youwoai)
3. **Idempotent**: All scripts use IF NOT EXISTS to be safe for re-running
4. **Order Matters**: Run scripts in numerical order (01, 02, 03, etc.)