-- Humansa v2 Test Environment Database Setup
-- This script creates all necessary tables for the Humansa medical system

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS humansa_appointments CASCADE;
DROP TABLE IF EXISTS humansa_appointment_slots CASCADE;
DROP TABLE IF EXISTS humansa_conversation_history CASCADE;
DROP TABLE IF EXISTS humansa_patient_profile CASCADE;
DROP TABLE IF EXISTS humansa_users CASCADE;
DROP TABLE IF EXISTS humansa_doctors CASCADE;
DROP TABLE IF EXISTS humansa_clinics CASCADE;
DROP TABLE IF EXISTS humansa_doctor_availability CASCADE;
DROP TABLE IF EXISTS humansa_health_packages CASCADE;
DROP TABLE IF EXISTS humansa_insurance_providers CASCADE;
DROP TABLE IF EXISTS humansa_patient_insurance CASCADE;

-- Create Users table (basic user authentication)
CREATE TABLE humansa_users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create Clinics table
CREATE TABLE humansa_clinics (
    clinic_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    region TEXT NOT NULL,
    address TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    operating_hours JSONB,
    facilities TEXT[],
    parking BOOLEAN DEFAULT FALSE,
    wheelchair_accessible BOOLEAN DEFAULT TRUE,
    nearest_mrt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Doctors table
CREATE TABLE humansa_doctors (
    doctor_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    specialty TEXT NOT NULL,
    sub_specialty TEXT,
    qualifications TEXT[],
    years_experience INTEGER,
    languages TEXT[],
    gender TEXT,
    clinic_id TEXT REFERENCES humansa_clinics(clinic_id),
    region TEXT,
    consultation_fee_min INTEGER,
    consultation_fee_max INTEGER,
    rating DECIMAL(2,1),
    consultation_types TEXT[],
    special_interests TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Patient Profile table (extends users)
CREATE TABLE humansa_patient_profile (
    user_id TEXT PRIMARY KEY REFERENCES humansa_users(user_id),
    profile_data JSONB NOT NULL DEFAULT '{}',
    medical_history JSONB DEFAULT '[]',
    current_medications JSONB DEFAULT '[]',
    allergies TEXT[] DEFAULT '{}',
    blood_type TEXT,
    emergency_contact JSONB,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Doctor Availability table
CREATE TABLE humansa_doctor_availability (
    availability_id SERIAL PRIMARY KEY,
    doctor_id TEXT REFERENCES humansa_doctors(doctor_id),
    day_of_week TEXT NOT NULL, -- Monday, Tuesday, etc.
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    consultation_type TEXT NOT NULL, -- in-person, telemedicine, both
    is_active BOOLEAN DEFAULT TRUE
);

-- Create Appointment Slots table
CREATE TABLE humansa_appointment_slots (
    slot_id TEXT PRIMARY KEY,
    doctor_id TEXT REFERENCES humansa_doctors(doctor_id),
    date DATE NOT NULL,
    time TIME NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    consultation_type TEXT NOT NULL,
    consultation_fee INTEGER,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doctor_id, date, time)
);

-- Create Appointments table
CREATE TABLE humansa_appointments (
    appointment_id TEXT PRIMARY KEY,
    slot_id TEXT REFERENCES humansa_appointment_slots(slot_id),
    user_id TEXT REFERENCES humansa_users(user_id),
    doctor_id TEXT REFERENCES humansa_doctors(doctor_id),
    clinic_id TEXT REFERENCES humansa_clinics(clinic_id),
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    consultation_type TEXT NOT NULL,
    status TEXT DEFAULT 'scheduled', -- scheduled, completed, cancelled, no-show
    reason_for_visit TEXT,
    notes TEXT,
    consultation_fee INTEGER,
    payment_status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancellation_reason TEXT
);

-- Create Conversation History table
CREATE TABLE humansa_conversation_history (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES humansa_users(user_id),
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Health Packages table
CREATE TABLE humansa_health_packages (
    package_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price INTEGER NOT NULL,
    promotional_price INTEGER,
    duration TEXT,
    tests JSONB NOT NULL,
    suitable_for TEXT[],
    preparation TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Insurance Providers table
CREATE TABLE humansa_insurance_providers (
    provider_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    coverage_type TEXT,
    is_panel BOOLEAN DEFAULT FALSE,
    coverage_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Patient Insurance table
CREATE TABLE humansa_patient_insurance (
    id SERIAL PRIMARY KEY,
    user_id TEXT REFERENCES humansa_users(user_id),
    provider_id INTEGER REFERENCES humansa_insurance_providers(provider_id),
    policy_number TEXT,
    coverage_start_date DATE,
    coverage_end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, provider_id, policy_number)
);

-- Create indexes for better query performance
CREATE INDEX idx_conversation_user_id ON humansa_conversation_history(user_id, created_at DESC);
CREATE INDEX idx_doctors_specialty ON humansa_doctors(specialty);
CREATE INDEX idx_doctors_region ON humansa_doctors(region);
CREATE INDEX idx_doctors_clinic ON humansa_doctors(clinic_id);
CREATE INDEX idx_appointments_user ON humansa_appointments(user_id);
CREATE INDEX idx_appointments_doctor ON humansa_appointments(doctor_id);
CREATE INDEX idx_appointments_date ON humansa_appointments(appointment_date);
CREATE INDEX idx_slots_doctor_date ON humansa_appointment_slots(doctor_id, date);
CREATE INDEX idx_slots_available ON humansa_appointment_slots(is_available, date);

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update timestamp triggers
CREATE TRIGGER update_humansa_clinics_updated_at BEFORE UPDATE ON humansa_clinics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_humansa_doctors_updated_at BEFORE UPDATE ON humansa_doctors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_humansa_patient_profile_updated_at BEFORE UPDATE ON humansa_patient_profile
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_humansa_appointments_updated_at BEFORE UPDATE ON humansa_appointments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();