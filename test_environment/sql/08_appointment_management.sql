-- Appointment Management Tables for Humansa V2
-- Adds proper patient management and appointment history tracking

-- Ensure patient table exists with proper structure
CREATE TABLE IF NOT EXISTS humansa_patient (
    patient_id VARCHAR(50) PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    id_number VARCHAR(50),
    gender VARCHAR(10),
    birth_date DATE,
    address TEXT,
    city VARCHAR(50),
    emergency_contact VARCHAR(100),
    emergency_phone VARCHAR(20),
    medical_history TEXT,
    allergies TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ensure appointment history table exists
CREATE TABLE IF NOT EXISTS humansa_appointment_history (
    appointment_id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES humansa_patient(patient_id),
    doctor_code VARCHAR(10) REFERENCES humansa_doctor(doctor_code),
    schedule_id INTEGER REFERENCES humansa_schedule(schedule_id),
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(50) DEFAULT 'confirmed', -- confirmed, cancelled, completed, no_show
    booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    check_in_time TIMESTAMP,
    completion_time TIMESTAMP,
    cancellation_time TIMESTAMP,
    cancellation_reason TEXT,
    notes TEXT,
    payment_status VARCHAR(50) DEFAULT 'pending', -- pending, paid, refunded
    amount DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_patient_phone ON humansa_patient(phone);
CREATE INDEX IF NOT EXISTS idx_patient_city ON humansa_patient(city);
CREATE INDEX IF NOT EXISTS idx_appointment_patient ON humansa_appointment_history(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointment_doctor ON humansa_appointment_history(doctor_code);
CREATE INDEX IF NOT EXISTS idx_appointment_date ON humansa_appointment_history(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointment_status ON humansa_appointment_history(status);

-- Add test patients for testing appointment flow
INSERT INTO humansa_patient (patient_id, phone, name, city, gender, birth_date) VALUES
('PAT_test_user_12', '13800138001', '测试用户12', '北京', '男', '1990-01-01'),
('PAT_test_user_13', '13800138002', '测试用户13', '上海', '女', '1985-05-15'),
('PAT_test_user_14', '13800138003', '测试用户14', '深圳', '男', '1992-08-20'),
('PAT_test_user_15', '13800138004', '测试用户15', '广州', '女', '1988-12-10')
ON CONFLICT (patient_id) DO NOTHING;

-- Add some sample appointment history for testing
INSERT INTO humansa_appointment_history 
(patient_id, doctor_code, appointment_date, appointment_time, status, amount, notes) 
VALUES
('PAT_test_user_14', 'TEST_001', CURRENT_DATE + INTERVAL '2 days', '09:00:00', 'confirmed', 300, '初诊'),
('PAT_test_user_14', 'TEST_003', CURRENT_DATE - INTERVAL '7 days', '14:00:00', 'completed', 150, '复诊')
ON CONFLICT DO NOTHING;

-- Ensure schedule table has proper constraints
ALTER TABLE humansa_schedule 
ADD CONSTRAINT IF NOT EXISTS positive_slots CHECK (remaining_slots >= 0);

-- Function to get appointment summary for a patient
CREATE OR REPLACE FUNCTION get_patient_appointment_summary(p_phone VARCHAR)
RETURNS TABLE (
    total_appointments BIGINT,
    completed_appointments BIGINT,
    upcoming_appointments BIGINT,
    cancelled_appointments BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_appointments,
        COUNT(CASE WHEN ah.status = 'completed' THEN 1 END) as completed_appointments,
        COUNT(CASE WHEN ah.status = 'confirmed' AND ah.appointment_date >= CURRENT_DATE THEN 1 END) as upcoming_appointments,
        COUNT(CASE WHEN ah.status = 'cancelled' THEN 1 END) as cancelled_appointments
    FROM humansa_appointment_history ah
    JOIN humansa_patient p ON ah.patient_id = p.patient_id
    WHERE p.phone = p_phone;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO postgres;