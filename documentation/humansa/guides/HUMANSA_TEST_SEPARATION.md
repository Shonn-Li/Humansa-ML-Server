# Test Environment Separation

## Current Setup

### 1. Main Test Environment (Existing)
- **Container**: `youwoai_test_db`
- **Port**: 5454
- **Database**: `youwoai_test`
- **User**: postgres
- **Password**: 031203
- **Location**: `/test_environment/docker-compose.yml`
- **Purpose**: General API testing, multi-agent testing

### 2. Humansa Test Environment (New)
- **Container**: `humansa_test_postgres`
- **Port**: 5456 (updated to avoid conflict)
- **Database**: `youwoai`
- **User**: youwo
- **Password**: youwo123
- **Location**: `/test_environment/docker-compose.test.yml`
- **Purpose**: Humansa v2 medical system testing

## ✅ No Conflicts

The environments are completely separated:

1. **Different Ports**: 
   - Main test: 5454
   - Humansa test: 5456

2. **Different Containers**:
   - Main test: `youwoai_test_db`
   - Humansa test: `humansa_test_postgres`

3. **Different Volumes**:
   - Main test: `test_pgdata`
   - Humansa test: `humansa_test_postgres_data`

4. **Different Users**:
   - Main test: postgres/031203
   - Humansa test: youwo/youwo123

## Usage

### Running Main Test Environment
```bash
cd test_environment
docker-compose up -d
# Uses port 5454
```

### Running Humansa Test Environment
```bash
cd test_environment
docker-compose -f docker-compose.test.yml up -d
# Uses port 5456
```

### Running Both Simultaneously
```bash
# Start main test DB
docker-compose up -d

# Start Humansa test DB
docker-compose -f docker-compose.test.yml up -d

# Both will run without conflicts
```

## Environment Variables

### For Main Test
```bash
export DB_PORT=5454
export DB_USER=postgres
export DB_PASSWORD=031203
```

### For Humansa Test
```bash
export DB_PORT=5456
export DB_USER=youwo
export DB_PASSWORD=youwo123
```

## Cleanup

### Clean Main Test Only
```bash
docker-compose down -v
```

### Clean Humansa Test Only
```bash
docker-compose -f docker-compose.test.yml down -v
# OR
./cleanup_test_env.sh
```

### Clean Both
```bash
docker-compose down -v
docker-compose -f docker-compose.test.yml down -v
```

## Benefits of Separation

1. **Independent Testing**: Can test Humansa features without affecting other tests
2. **Different Schemas**: Humansa has specialized medical tables
3. **Different Data**: Humansa has medical test data (doctors, patients, appointments)
4. **Parallel Development**: Teams can work on different features simultaneously
5. **Easy Reset**: Each environment can be reset independently

## Summary

- ✅ No port conflicts (5454 vs 5456)
- ✅ No container name conflicts
- ✅ No volume conflicts
- ✅ Can run simultaneously
- ✅ Completely isolated environments