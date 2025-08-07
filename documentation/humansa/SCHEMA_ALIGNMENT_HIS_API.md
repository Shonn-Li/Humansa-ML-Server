# HIS API Schema Alignment Documentation

## Executive Summary

This document outlines the schema alignment between Humansa's database and the HIS (Hospital Information System) API requirements.

## Current Schema Issues and Fixes

### 1. Doctor Schedule Table Schema

**HIS API Expected Response Format:**
```json
{
  "schDate": "2025-07-22",
  "shiftInfo": {
    "shiftId": "xxx",
    "startTime": "09:00",
    "endTime": "12:00",
    "remainingCapacity": 5
  }
}
```

**Current Database Schema (CORRECT):**
```sql
CREATE TABLE humansa_schedule (
    schedule_id SERIAL PRIMARY KEY,
    doctor_code VARCHAR(10),
    clinic_code VARCHAR(10),
    shift_date DATE NOT NULL,        -- Matches "schDate"
    start_time TIME NOT NULL,         -- Matches "startTime"
    end_time TIME NOT NULL,           -- Matches "endTime"
    remaining_slots INTEGER DEFAULT 10 -- Matches "remainingCapacity"
);
```

**Schema Mismatch Found:**
- `humansa_test_doctors.sql` incorrectly uses `schedule_date` instead of `shift_date`
- Fixed column names to match main schema

### 2. Doctor Table Schema

**HIS API Expected Fields:**
```json
{
  "doctorId": "6e690c4a49664f4993a21690a83d4726",
  "doctorName": "邹威",
  "deptId": "xxx",
  "deptName": "骨科",
  "hospitalId": "6"
}
```

**Current Database Schema:**
```sql
CREATE TABLE humansa_doctor (
    doctor_code VARCHAR(10) PRIMARY KEY,  -- Maps to "doctorId"
    name VARCHAR(100) NOT NULL,           -- Maps to "doctorName"
    specialty VARCHAR(100),               -- Maps to "deptName"
    clinic_code VARCHAR(10),              -- Maps to "hospitalId"
    -- Missing: deptId (department ID)
);
```

**Gap:** Missing department ID concept

### 3. Clinic Table Schema

**HIS API Expected Fields:**
```json
{
  "hospitalId": "6",
  "hospitalName": "友邦峻宇养生庭",
  "address": "xxx",
  "phone": "xxx"
}
```

**Current Database Schema:**
```sql
CREATE TABLE humansa_clinic (
    clinic_code VARCHAR(10) PRIMARY KEY,  -- Maps to "hospitalId"
    name VARCHAR(100) NOT NULL,           -- Maps to "hospitalName"
    address TEXT,
    phone VARCHAR(20),
    city VARCHAR(50),
    operating_hours TEXT
);
```

**Status:** ✅ Schema aligns correctly

### 4. Patient Management (CRITICAL GAP)

**HIS API Expected:**
- Patient ID (`pid`)
- Phone-based lookup
- Appointment history tracking

**Current System:**
- No patient persistence
- Only collects name/phone at booking time
- No appointment history

**Required Schema Addition:**
```sql
CREATE TABLE humansa_patient (
    patient_id VARCHAR(50) PRIMARY KEY,  -- Maps to "pid"
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE humansa_appointment_history (
    appointment_id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES humansa_patient(patient_id),
    doctor_code VARCHAR(10) REFERENCES humansa_doctor(doctor_code),
    schedule_id INTEGER REFERENCES humansa_schedule(schedule_id),
    appointment_date DATE,
    appointment_time TIME,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5. Department Structure (MISSING)

**HIS API Expected:**
- Department ID (`deptId`)
- Department-based doctor organization

**Required Schema Addition:**
```sql
CREATE TABLE humansa_department (
    dept_id VARCHAR(20) PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    clinic_code VARCHAR(10) REFERENCES humansa_clinic(clinic_code)
);

-- Modify doctor table to include department
ALTER TABLE humansa_doctor ADD COLUMN dept_id VARCHAR(20) REFERENCES humansa_department(dept_id);
```

## API Response Format Mapping

### 1. Doctor Availability Response

**HIS Format:**
```json
{
  "code": 0,
  "data": [
    {
      "shiftId": "xxx",
      "doctorId": "xxx",
      "doctorName": "张三",
      "deptId": "xxx",
      "deptName": "骨科",
      "schDate": "2025-07-22",
      "startTime": "09:00",
      "endTime": "12:00",
      "totalCapacity": 10,
      "bookedCount": 3,
      "remainingCapacity": 7
    }
  ]
}
```

**Our Response Mapping:**
```python
{
    "shift_id": row["schedule_id"],          # Maps to shiftId
    "doctor_id": row["doctor_code"],         # Maps to doctorId
    "doctor_name": row["doctor_name"],       # Maps to doctorName
    "dept_id": row["dept_id"],               # Maps to deptId (needs addition)
    "dept_name": row["specialty"],           # Maps to deptName
    "sch_date": row["shift_date"],           # Maps to schDate
    "start_time": row["start_time"],         # Maps to startTime
    "end_time": row["end_time"],             # Maps to endTime
    "remaining_capacity": row["remaining_slots"] # Maps to remainingCapacity
}
```

### 2. Doctor Search Response

**HIS Format:**
```json
{
  "code": 0,
  "data": [
    {
      "doctorId": "xxx",
      "doctorName": "李四",
      "title": "主任医师",
      "deptId": "xxx",
      "deptName": "内科",
      "hospitalId": "6",
      "hospitalName": "北京诊所",
      "expertise": "心血管疾病",
      "registrationFee": 300
    }
  ]
}
```

**Our Response Mapping:**
```python
{
    "doctor_id": row["doctor_code"],
    "doctor_name": row["name"],
    "title": row["title"],
    "dept_id": row["dept_id"],  # Needs addition
    "dept_name": row["specialty"],
    "hospital_id": row["clinic_code"],
    "hospital_name": row["clinic_name"],
    "expertise": row["expertise"],
    "registration_fee": row["registration_fee"]
}
```

## Implementation Priority

### Critical (Blocking Issues):
1. ✅ Fix `shift_date` column name in test data SQL
2. ❌ Add patient management tables
3. ❌ Add appointment history tracking
4. ❌ Add department structure

### High Priority:
5. ❌ Update response format to match HIS API
6. ❌ Add ID mapping tables
7. ❌ Implement phone-based patient lookup

### Medium Priority:
8. ❌ Support batch doctor ID queries
9. ❌ Add shift-based scheduling
10. ❌ Implement package/membership system

## Database Migration Script

```sql
-- 1. Add department table
CREATE TABLE IF NOT EXISTS humansa_department (
    dept_id VARCHAR(20) PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    clinic_code VARCHAR(10) REFERENCES humansa_clinic(clinic_code)
);

-- 2. Add patient table
CREATE TABLE IF NOT EXISTS humansa_patient (
    patient_id VARCHAR(50) PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    email VARCHAR(100),
    id_number VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Add appointment history
CREATE TABLE IF NOT EXISTS humansa_appointment_history (
    appointment_id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES humansa_patient(patient_id),
    doctor_code VARCHAR(10) REFERENCES humansa_doctor(doctor_code),
    schedule_id INTEGER REFERENCES humansa_schedule(schedule_id),
    appointment_date DATE,
    appointment_time TIME,
    status VARCHAR(50) DEFAULT 'confirmed',
    booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- 4. Add department reference to doctors
ALTER TABLE humansa_doctor ADD COLUMN IF NOT EXISTS dept_id VARCHAR(20);

-- 5. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_patient_phone ON humansa_patient(phone);
CREATE INDEX IF NOT EXISTS idx_appointment_patient ON humansa_appointment_history(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointment_date ON humansa_appointment_history(appointment_date);
```

## Validation Checklist

- [x] Database schema has correct column names
- [x] Test data SQL uses correct column names
- [ ] Patient management system implemented
- [ ] Department structure added
- [ ] Appointment history tracking added
- [ ] Response format matches HIS API
- [ ] ID mapping system in place
- [ ] Phone-based patient lookup works
- [ ] Batch queries supported

## Next Steps

1. Run the migration script to add missing tables
2. Update the Python code to use new schema
3. Modify response format to match HIS API
4. Test with the corrected data
5. Implement patient registration flow