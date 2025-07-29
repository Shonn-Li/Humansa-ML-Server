-- Fix doctor table schema to ensure consistency
-- This script handles the mismatch between doctor_id and doctor_code

-- First, drop dependent objects
DROP TABLE IF EXISTS humansa_appointment_history CASCADE;
DROP TABLE IF EXISTS humansa_schedule CASCADE;
DROP TABLE IF EXISTS humansa_doctor CASCADE;

-- Recreate doctor table with consistent schema
CREATE TABLE humansa_doctor (
    doctor_id VARCHAR(10) PRIMARY KEY,  -- Using doctor_id as primary key
    doctor_code VARCHAR(10) UNIQUE,     -- Keep doctor_code for compatibility
    name VARCHAR(100) NOT NULL,
    specialty VARCHAR(100),
    qualifications TEXT,
    experience_years INTEGER,
    languages TEXT[],
    clinic_code VARCHAR(10),
    consultation_fee DECIMAL(10,2),
    title VARCHAR(100),
    expertise TEXT,
    rating DECIMAL(2,1),
    bio TEXT,
    registration_fee INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for better performance
CREATE INDEX idx_doctor_specialty ON humansa_doctor(specialty);
CREATE INDEX idx_doctor_clinic ON humansa_doctor(clinic_code);
CREATE INDEX idx_doctor_name ON humansa_doctor(name);

-- Recreate schedule table with correct references
CREATE TABLE humansa_schedule (
    schedule_id SERIAL PRIMARY KEY,
    doctor_id VARCHAR(10) REFERENCES humansa_doctor(doctor_id),
    doctor_code VARCHAR(10),  -- Keep for compatibility
    clinic_code VARCHAR(10),
    shift_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    available_slots INTEGER DEFAULT 12,
    booked_slots INTEGER DEFAULT 0,
    remaining_slots INTEGER GENERATED ALWAYS AS (available_slots - booked_slots) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doctor_id, shift_date, start_time)
);

-- Create indexes for schedule
CREATE INDEX idx_schedule_date ON humansa_schedule(shift_date);
CREATE INDEX idx_schedule_doctor ON humansa_schedule(doctor_id);
CREATE INDEX idx_schedule_availability ON humansa_schedule(shift_date, remaining_slots);

-- Recreate appointment history table
CREATE TABLE humansa_appointment_history (
    appointment_id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50),
    doctor_id VARCHAR(10) REFERENCES humansa_doctor(doctor_id),
    schedule_id INTEGER REFERENCES humansa_schedule(schedule_id),
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(50) DEFAULT 'confirmed',
    booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    check_in_time TIMESTAMP,
    completion_time TIMESTAMP,
    cancellation_time TIMESTAMP,
    cancellation_reason TEXT,
    notes TEXT,
    payment_status VARCHAR(50) DEFAULT 'pending',
    amount DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create patient table if not exists
CREATE TABLE IF NOT EXISTS humansa_patient (
    patient_id VARCHAR(50) PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    gender VARCHAR(10),
    birth_date DATE,
    email VARCHAR(100),
    address TEXT,
    emergency_contact VARCHAR(100),
    emergency_phone VARCHAR(20),
    medical_history TEXT,
    allergies TEXT,
    current_medications TEXT,
    insurance_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add foreign key for appointment history
ALTER TABLE humansa_appointment_history 
ADD CONSTRAINT fk_appointment_patient 
FOREIGN KEY (patient_id) REFERENCES humansa_patient(patient_id);

-- Create trigger to sync doctor_code with doctor_id
CREATE OR REPLACE FUNCTION sync_doctor_code()
RETURNS TRIGGER AS $$
BEGIN
    -- If doctor_code is not provided, use doctor_id
    IF NEW.doctor_code IS NULL THEN
        NEW.doctor_code := NEW.doctor_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER doctor_code_sync
BEFORE INSERT OR UPDATE ON humansa_doctor
FOR EACH ROW
EXECUTE FUNCTION sync_doctor_code();

-- Create similar trigger for schedule
CREATE OR REPLACE FUNCTION sync_schedule_doctor_code()
RETURNS TRIGGER AS $$
BEGIN
    -- Sync doctor_code from doctor table
    SELECT doctor_code INTO NEW.doctor_code 
    FROM humansa_doctor 
    WHERE doctor_id = NEW.doctor_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER schedule_doctor_code_sync
BEFORE INSERT OR UPDATE ON humansa_schedule
FOR EACH ROW
EXECUTE FUNCTION sync_schedule_doctor_code();