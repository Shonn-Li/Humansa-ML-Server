-- Combined initialization script for test instances (ports 5061-5064)
-- This script sets up a complete Humansa test database instance

-- 1. Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Core Humansa Tables (from 02_core_tables.sql)
-- [Including all tables from the previous file]

-- Patients table
CREATE TABLE IF NOT EXISTS patients (
    patient_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(20),
    phone VARCHAR(20),
    email VARCHAR(100),
    address TEXT,
    medical_history JSONB DEFAULT '[]'::jsonb,
    allergies TEXT[],
    current_medications TEXT[],
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),
    insurance_provider VARCHAR(100),
    insurance_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Doctors table  
CREATE TABLE IF NOT EXISTS doctors (
    doctor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    specialization VARCHAR(100),
    department VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    available_slots JSONB DEFAULT '[]'::jsonb,
    consultation_fee DECIMAL(10,2),
    years_of_experience INTEGER,
    qualifications TEXT[],
    languages_spoken TEXT[],
    clinic_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Appointments table
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(patient_id),
    doctor_id UUID REFERENCES doctors(doctor_id),
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    duration INTEGER DEFAULT 30,
    appointment_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'scheduled',
    notes TEXT,
    symptoms TEXT,
    diagnosis TEXT,
    prescription JSONB,
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Medical Records table
CREATE TABLE IF NOT EXISTS medical_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(patient_id),
    doctor_id UUID REFERENCES doctors(doctor_id),
    appointment_id UUID REFERENCES appointments(appointment_id),
    visit_date DATE,
    chief_complaint TEXT,
    diagnosis TEXT,
    treatment_plan TEXT,
    prescriptions JSONB,
    lab_results JSONB,
    vital_signs JSONB,
    doctor_notes TEXT,
    attachments TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Clinics table
CREATE TABLE IF NOT EXISTS clinics (
    clinic_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_name VARCHAR(200) NOT NULL,
    clinic_code VARCHAR(50) UNIQUE,
    address TEXT,
    city VARCHAR(100),
    province VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    operating_hours JSONB,
    services TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Mem0 Memory Tables
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    context_type VARCHAR(50),
    context_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Humansa-specific tables
CREATE TABLE IF NOT EXISTS humansa_patient_profile (
    user_id TEXT PRIMARY KEY,
    profile_data JSONB NOT NULL DEFAULT '{}',
    medical_history JSONB DEFAULT '[]',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS humansa_conversation_history (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Create indexes
CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON appointments(doctor_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_medical_records_patient ON medical_records(patient_id);
CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_conversation_user_id ON humansa_conversation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_id ON humansa_conversation_history(conversation_id);

-- 6. Create update triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_patients_updated_at BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_doctors_updated_at BEFORE UPDATE ON doctors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_appointments_updated_at BEFORE UPDATE ON appointments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 7. Insert sample test data
INSERT INTO clinics (clinic_id, clinic_name, clinic_code, city, province) VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '诺亚新舟北京诊所', 'BJ001', '北京', '北京市'),
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '诺亚新舟上海诊所', 'SH001', '上海', '上海市')
ON CONFLICT DO NOTHING;

INSERT INTO doctors (doctor_id, first_name, last_name, specialization, department, clinic_id) VALUES
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '李', '医生', '心脏科', '内科', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '张', '医生', '骨科', '外科', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', '王', '医生', '儿科', '儿科', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12')
ON CONFLICT DO NOTHING;

INSERT INTO patients (patient_id, first_name, last_name, date_of_birth, gender, phone, email) VALUES
    ('p0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Test', 'Patient', '1990-01-01', 'M', '13800138000', 'test@example.com')
ON CONFLICT DO NOTHING;

-- Grant permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO youwo;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO youwo;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO youwo;