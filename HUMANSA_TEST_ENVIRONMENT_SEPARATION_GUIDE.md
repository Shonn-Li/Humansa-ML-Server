# Humansa Test Environment Separation Guide

## Overview

This guide documents the complete separation strategy between the main test environment and the Humansa test environment. Both environments are designed to run independently without any conflicts.

## Environment Architecture

### 1. Main Test Environment
**Purpose**: General API testing, multi-agent features, RAG functionality

- **Location**: `/test_environment/`
- **Port**: 5454
- **Container**: `youwoai_test_db`
- **Database**: `youwoai_test`
- **Credentials**: postgres/031203
- **Docker Compose**: `docker-compose.yml`
- **Test Files**: `/test/` (excluding Humansa-specific tests)

### 2. Humansa Test Environment
**Purpose**: Medical consultation system testing with specialized healthcare data

- **Location**: `/humansa_test_environment/`
- **Port**: 5456
- **Container**: `humansa_test_postgres`
- **Database**: `youwoai`
- **Credentials**: youwo/youwo123
- **Docker Compose**: `docker/docker-compose.yml`
- **Test Files**: `/humansa_test_environment/tests/`

### 3. Future Humansa V2 Environment (Per Requirements)
**Purpose**: V2 multi-agent medical system with advanced features

- **Proposed Port**: 5003 (as specified in requirements)
- **Container**: `humansa_v2_postgres`
- **Features**: Multi-agent orchestration, patient profiles, advanced RAG

## Separation Strategy

### 1. Infrastructure Isolation

#### Ports
- Main: 5454
- Humansa V1: 5456
- Humansa V2: 5003 (proposed)
- No port conflicts when running simultaneously

#### Docker Resources
```yaml
# Main Test
container_name: youwoai_test_db
volumes:
  - test_pgdata:/var/lib/postgresql/data

# Humansa Test
container_name: humansa_test_postgres
volumes:
  - humansa_test_postgres_data:/var/lib/postgresql/data
```

#### Network Isolation
- Each environment uses Docker's bridge network
- No cross-environment communication required

### 2. File Organization

#### Current Structure
```
YouWoAI-ML-Server/
├── test_environment/              # Main test environment
│   ├── docker-compose.yml
│   └── sql/
├── humansa_test_environment/      # Humansa test environment
│   ├── docker/
│   ├── sql/
│   ├── scripts/
│   └── tests/
└── test/                         # All test files
    ├── core/                     # Core API tests
    ├── integration/              # Integration tests
    └── multi_agent/              # Multi-agent tests
```

#### Recommended Improvements
1. Move Humansa V2 test files from root to proper location:
   ```bash
   # Files to move:
   test_humansa_v2.py
   test_humansa_v2_comprehensive.py
   test_humansa_v2_direct.py
   test_humansa_v2_standalone.py
   
   # Move to:
   humansa_test_environment/tests/v2/
   ```

2. Create V2-specific directory structure:
   ```
   humansa_test_environment/
   ├── v1/                        # Current Humansa implementation
   └── v2/                        # New multi-agent system
       ├── docker/
       ├── sql/
       └── tests/
   ```

### 3. Database Schema Separation

#### Main Test Database
- Tables: users, notes, embeddings, conversations
- Focus: General application features
- Data: Generic test data

#### Humansa Test Database
- Tables: doctors, patients, appointments, clinics, services
- Focus: Medical consultation system
- Data: Healthcare-specific test data

### 4. Code Separation

#### API Endpoints
- Main: `/v1/*` endpoints
- Humansa V1: `/v1-humansa/*`, `/humansa/*`
- Humansa V2: `/v2/humansa/*` (proposed)

#### Agent Implementation
- Main: `src/chat/agent/`
- Humansa V1: `src/humansa/`
- Humansa V2: `src/humansa/v2/` (exists)

## Maintenance Guidelines

### 1. Starting Environments

#### Single Environment
```bash
# Main test only
cd test_environment && docker-compose up -d

# Humansa test only
cd humansa_test_environment && ./setup.sh
```

#### Both Environments
```bash
# Start both (no conflicts)
cd test_environment && docker-compose up -d
cd ../humansa_test_environment && ./setup.sh
```

### 2. Environment Variables

#### For Main Test
```bash
export DB_HOST=localhost
export DB_PORT=5454
export DB_USER=postgres
export DB_PASSWORD=031203
export DB_NAME=youwoai_test
```

#### For Humansa Test
```bash
export DB_HOST=localhost
export DB_PORT=5456
export DB_USER=youwo
export DB_PASSWORD=youwo123
export DB_NAME=youwoai
```

### 3. Testing Best Practices

1. **Isolation**: Never cross-reference data between environments
2. **Configuration**: Use environment-specific config files
3. **Dependencies**: Each environment should be self-contained
4. **Documentation**: Update README files when making changes

### 4. Adding New Features

#### To Main Environment
1. Add migrations to `/test_environment/sql/`
2. Update test data scripts
3. Add tests to `/test/` appropriate subdirectory

#### To Humansa Environment
1. Add migrations to `/humansa_test_environment/sql/`
2. Update population scripts in `/scripts/`
3. Add tests to `/humansa_test_environment/tests/`

## Troubleshooting

### Port Conflicts
```bash
# Check if ports are in use
lsof -i :5454  # Main test
lsof -i :5456  # Humansa test
lsof -i :5003  # Humansa V2 (future)
```

### Container Conflicts
```bash
# List all containers
docker ps -a

# Remove specific container
docker rm -f youwoai_test_db           # Main
docker rm -f humansa_test_postgres      # Humansa
```

### Volume Cleanup
```bash
# List volumes
docker volume ls

# Remove specific volume
docker volume rm test_pgdata                    # Main
docker volume rm humansa_test_postgres_data     # Humansa
```

## Migration Path for V2

When implementing Humansa V2 as per requirements:

1. **Option A**: Update existing Humansa test (port 5456)
   - Pros: Reuse existing infrastructure
   - Cons: May break V1 testing

2. **Option B**: Create new environment (port 5003)
   - Pros: Complete isolation, follows requirements
   - Cons: Additional resource usage

3. **Recommended**: Option B for development, then consolidate

## Summary

The test environments are properly separated with:
- ✅ No port conflicts
- ✅ No container name conflicts  
- ✅ No volume conflicts
- ✅ Independent schemas
- ✅ Separate test suites
- ✅ Can run simultaneously

This separation enables:
- Parallel development
- Independent testing
- Clean environments
- Easy debugging
- Scalable architecture