# Database Schema Fixes for Test Dashboard

## Overview
This document describes the database schema fixes applied to ensure the test dashboard's 4 ML server instances (ports 6011-6014) work correctly with their corresponding test databases (ports 5061-5064).

## Key Issues Fixed

### 1. Missing Tables
The test databases were missing critical tables required by the Humansa system:
- `humansa_medical_service` - stores medical service offerings
- Proper test data for `humansa_clinics` and `humansa_doctor`

### 2. Column Name Mismatches
The code expected different column names than what existed in the database:
- Code used `clinic_code` but initial setup used `clinic_id`
- Code used `humansa_doctor` (singular) but setup created `humansa_doctors` (plural)
- Various JOIN conditions were using mismatched column names

### 3. Standardization with Test Environment
The test dashboard databases needed to match the standardized test environment (port 5454) schema and data.

## Fixes Applied

### 1. Schema Corrections
- Changed all `clinic_id` references to `clinic_code` to match test environment
- Created `humansa_doctor` table (singular) to replace `humansa_doctors` (plural)
- Added missing `humansa_medical_service` table with proper columns

### 2. Code Updates
Updated the following files to use correct column names:
- `/src/humansa/postgres/database.py` - fixed all SQL queries
- `/src/humansa/v2/agents/appointment_agent.py` - fixed JOIN conditions
- `/src/humansa/v2/tools/db_medical_tools.py` - fixed service queries

### 3. Standardized Test Data
Applied standardized test data from test environment including:
- 11 clinics (H1-H5, CL001-CL003, CLINIC001-CLINIC003)
- 9 doctors (D1-D5, DOC001-DOC004)
- 25 medical services (SVC001-SVC025)

## Database Schema

### humansa_clinics
```sql
CREATE TABLE humansa_clinics (
    clinic_code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address TEXT,
    phone VARCHAR(20),
    region VARCHAR(50),
    type VARCHAR(50)
);
```

### humansa_doctor
```sql
CREATE TABLE humansa_doctor (
    doctor_code VARCHAR(10) PRIMARY KEY,
    clinic_code VARCHAR(10) REFERENCES humansa_clinics(clinic_code),
    name VARCHAR(100) NOT NULL,
    title VARCHAR(100),
    expertise TEXT,
    bio TEXT,
    registration_fee INTEGER
);
```

### humansa_medical_service
```sql
CREATE TABLE humansa_medical_service (
    service_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10,2),
    clinic_code TEXT REFERENCES humansa_clinics(clinic_code),
    -- Additional columns for compatibility
    price_range_min DECIMAL(10,2),
    price_range_max DECIMAL(10,2),
    duration_minutes INTEGER DEFAULT 30,
    category TEXT,
    is_active BOOLEAN DEFAULT TRUE
);
```

## SQL Scripts
The following SQL scripts were created to apply fixes:
1. `apply_standardized_test_data.sql` - Main script to fix schema and apply test data
2. `add_missing_tables.sql` - Initial script to add missing tables
3. `fix_clinic_code.sql` - Script to fix column name issues
4. `populate_clinics.sql` - Script to add clinic test data

## Verification
All 4 test databases now have identical data:
- Database 1 (port 5061): 11 clinics, 9 doctors, 25 services
- Database 2 (port 5062): 11 clinics, 9 doctors, 25 services
- Database 3 (port 5063): 11 clinics, 9 doctors, 25 services
- Database 4 (port 5064): 11 clinics, 9 doctors, 25 services

## Testing
After applying fixes, ML servers successfully:
- Return health checkup services
- Use proper table and column names
- Query standardized test data
- No more "table does not exist" errors
- No more "column does not exist" errors