-- Create missing Humansa tables
-- This ensures we have all necessary tables before running migrations

-- Create doctors table if not exists
CREATE TABLE IF NOT EXISTS humansa_doctor (
    doctor_code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    title VARCHAR(100),
    specialty VARCHAR(100),
    expertise TEXT,
    experience_years INTEGER,
    clinic_code VARCHAR(10),
    rating DECIMAL(2,1),
    bio TEXT,
    registration_fee INTEGER
);

-- Create schedule table if not exists  
CREATE TABLE IF NOT EXISTS humansa_schedule (
    schedule_id SERIAL PRIMARY KEY,
    doctor_code VARCHAR(10) REFERENCES humansa_doctor(doctor_code),
    clinic_code VARCHAR(10),
    shift_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    remaining_slots INTEGER DEFAULT 10,
    UNIQUE(doctor_code, shift_date, start_time)
);

-- Ensure appointment history table exists with proper structure
CREATE TABLE IF NOT EXISTS humansa_appointment_history (
    appointment_id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES humansa_patient(patient_id),
    doctor_code VARCHAR(10) REFERENCES humansa_doctor(doctor_code),
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_appointment_patient ON humansa_appointment_history(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointment_doctor ON humansa_appointment_history(doctor_code);
CREATE INDEX IF NOT EXISTS idx_appointment_date ON humansa_appointment_history(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointment_status ON humansa_appointment_history(status);

-- Add constraint to schedule table
ALTER TABLE humansa_schedule 
DROP CONSTRAINT IF EXISTS positive_slots;

ALTER TABLE humansa_schedule 
ADD CONSTRAINT positive_slots CHECK (remaining_slots >= 0);