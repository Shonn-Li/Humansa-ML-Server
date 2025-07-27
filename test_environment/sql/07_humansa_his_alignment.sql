-- Humansa HIS API Schema Alignment Migration
-- This script adds missing tables and columns to align with HIS API requirements

-- 1. Add department table
CREATE TABLE IF NOT EXISTS humansa_department (
    dept_id VARCHAR(20) PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    clinic_code VARCHAR(10) REFERENCES humansa_clinic(clinic_code),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Add patient table (critical for HIS API)
CREATE TABLE IF NOT EXISTS humansa_patient (
    patient_id VARCHAR(50) PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    email VARCHAR(100),
    id_number VARCHAR(50),
    gender VARCHAR(10),
    birth_date DATE,
    address TEXT,
    emergency_contact VARCHAR(100),
    emergency_phone VARCHAR(20),
    medical_history TEXT,
    allergies TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Add appointment history table
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
    amount DECIMAL(10,2)
);

-- 4. Add package/membership tables
CREATE TABLE IF NOT EXISTS humansa_package_template (
    template_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2),
    valid_days INTEGER,
    services_included TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS humansa_patient_package (
    instance_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES humansa_patient(patient_id),
    template_id VARCHAR(50) REFERENCES humansa_package_template(template_id),
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiry_date DATE,
    status VARCHAR(50) DEFAULT 'active', -- active, expired, cancelled
    remaining_services JSONB
);

-- 5. Add VIP membership table
CREATE TABLE IF NOT EXISTS humansa_vip_account (
    account_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES humansa_patient(patient_id),
    membership_level VARCHAR(50), -- silver, gold, platinum
    start_date DATE,
    expiry_date DATE,
    points INTEGER DEFAULT 0,
    benefits JSONB,
    status VARCHAR(50) DEFAULT 'active'
);

-- 6. Add ID mapping tables for integration
CREATE TABLE IF NOT EXISTS humansa_id_mapping (
    mapping_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL, -- patient, doctor, clinic, department
    our_id VARCHAR(50) NOT NULL,
    his_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, our_id),
    UNIQUE(entity_type, his_id)
);

-- 7. Add columns to existing tables
ALTER TABLE humansa_doctor ADD COLUMN IF NOT EXISTS dept_id VARCHAR(20);
ALTER TABLE humansa_doctor ADD COLUMN IF NOT EXISTS doctor_his_id VARCHAR(50);

ALTER TABLE humansa_clinic ADD COLUMN IF NOT EXISTS hospital_his_id VARCHAR(20);
ALTER TABLE humansa_clinic ADD COLUMN IF NOT EXISTS cp_id VARCHAR(20); -- clinic internal code

-- 8. Add test departments
INSERT INTO humansa_department (dept_id, dept_name, clinic_code) VALUES
('DEPT001', '心脏科', 'CLINIC001'),
('DEPT002', '骨科', 'CLINIC001'),
('DEPT003', '内科', 'CLINIC001'),
('DEPT004', '儿科', 'CLINIC001'),
('DEPT005', '中医科', 'CLINIC001'),
('DEPT006', '心脏科', 'CLINIC002'),
('DEPT007', '骨科', 'CLINIC002'),
('DEPT008', '内科', 'CLINIC002'),
('DEPT009', '妇产科', 'CLINIC002'),
('DEPT010', '眼科', 'CLINIC002'),
('DEPT011', '全科', 'CLINIC003'),
('DEPT012', '中医科', 'CLINIC003'),
('DEPT013', '皮肤科', 'CLINIC003'),
('DEPT014', '耳鼻喉科', 'CLINIC003'),
('DEPT015', '口腔科', 'CLINIC003')
ON CONFLICT (dept_id) DO NOTHING;

-- 9. Update doctors with department IDs
UPDATE humansa_doctor SET dept_id = 'DEPT001' WHERE specialty = '心脏科' AND clinic_code = 'CLINIC001';
UPDATE humansa_doctor SET dept_id = 'DEPT002' WHERE specialty = '骨科' AND clinic_code = 'CLINIC001';
UPDATE humansa_doctor SET dept_id = 'DEPT003' WHERE specialty = '内科' AND clinic_code = 'CLINIC001';
UPDATE humansa_doctor SET dept_id = 'DEPT004' WHERE specialty = '儿科' AND clinic_code = 'CLINIC001';
UPDATE humansa_doctor SET dept_id = 'DEPT005' WHERE specialty = '中医科' AND clinic_code = 'CLINIC001';
UPDATE humansa_doctor SET dept_id = 'DEPT006' WHERE specialty = '心脏科' AND clinic_code = 'CLINIC002';
UPDATE humansa_doctor SET dept_id = 'DEPT007' WHERE specialty = '骨科' AND clinic_code = 'CLINIC002';
UPDATE humansa_doctor SET dept_id = 'DEPT008' WHERE specialty = '内科' AND clinic_code = 'CLINIC002';
UPDATE humansa_doctor SET dept_id = 'DEPT009' WHERE specialty = '妇产科' AND clinic_code = 'CLINIC002';
UPDATE humansa_doctor SET dept_id = 'DEPT010' WHERE specialty = '眼科' AND clinic_code = 'CLINIC002';
UPDATE humansa_doctor SET dept_id = 'DEPT011' WHERE specialty = '全科' AND clinic_code = 'CLINIC003';
UPDATE humansa_doctor SET dept_id = 'DEPT012' WHERE specialty = '中医科' AND clinic_code = 'CLINIC003';
UPDATE humansa_doctor SET dept_id = 'DEPT013' WHERE specialty = '皮肤科' AND clinic_code = 'CLINIC003';
UPDATE humansa_doctor SET dept_id = 'DEPT014' WHERE specialty = '耳鼻喉科' AND clinic_code = 'CLINIC003';
UPDATE humansa_doctor SET dept_id = 'DEPT015' WHERE specialty = '口腔科' AND clinic_code = 'CLINIC003';

-- 10. Add test patients
INSERT INTO humansa_patient (patient_id, phone, name, gender, birth_date, address) VALUES
('PAT001', '13800138000', '李明', '男', '1990-05-15', '北京市朝阳区'),
('PAT002', '13900139000', '王芳', '女', '1985-08-20', '上海市浦东新区'),
('PAT003', '13700137000', '张三', '男', '1978-03-10', '北京市海淀区'),
('PAT004', '13600136000', '刘静', '女', '1992-11-25', '深圳市福田区'),
('PAT005', '13500135000', '陈伟', '男', '1980-07-08', '广州市天河区')
ON CONFLICT (patient_id) DO NOTHING;

-- 11. Add sample appointment history
INSERT INTO humansa_appointment_history (patient_id, doctor_code, appointment_date, appointment_time, status, amount) VALUES
('PAT001', 'TEST_001', CURRENT_DATE - INTERVAL '7 days', '09:00:00', 'completed', 300),
('PAT001', 'TEST_003', CURRENT_DATE - INTERVAL '30 days', '14:00:00', 'completed', 150),
('PAT002', 'TEST_002', CURRENT_DATE - INTERVAL '14 days', '10:00:00', 'completed', 200),
('PAT003', 'TEST_006', CURRENT_DATE - INTERVAL '3 days', '15:00:00', 'cancelled', 0),
('PAT004', 'TEST_004', CURRENT_DATE + INTERVAL '3 days', '11:00:00', 'confirmed', 180),
('PAT005', 'TEST_005', CURRENT_DATE + INTERVAL '5 days', '09:30:00', 'confirmed', 250);

-- 12. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_patient_phone ON humansa_patient(phone);
CREATE INDEX IF NOT EXISTS idx_patient_name ON humansa_patient(name);
CREATE INDEX IF NOT EXISTS idx_appointment_patient ON humansa_appointment_history(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointment_doctor ON humansa_appointment_history(doctor_code);
CREATE INDEX IF NOT EXISTS idx_appointment_date ON humansa_appointment_history(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointment_status ON humansa_appointment_history(status);
CREATE INDEX IF NOT EXISTS idx_doctor_dept ON humansa_doctor(dept_id);
CREATE INDEX IF NOT EXISTS idx_dept_clinic ON humansa_department(clinic_code);
CREATE INDEX IF NOT EXISTS idx_mapping_lookup ON humansa_id_mapping(entity_type, our_id);
CREATE INDEX IF NOT EXISTS idx_mapping_reverse ON humansa_id_mapping(entity_type, his_id);

-- 13. Grant permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- 14. Add sample ID mappings for testing
INSERT INTO humansa_id_mapping (entity_type, our_id, his_id) VALUES
('clinic', 'CLINIC001', '6'),
('clinic', 'CLINIC002', '7'),
('clinic', 'CLINIC003', '8'),
('doctor', 'TEST_001', '6e690c4a49664f4993a21690a83d4726'),
('doctor', 'TEST_002', '0d46427c23654a078b09d76cd9b45aa1'),
('patient', 'PAT001', '52ac24b073fe430889778f56902415bd')
ON CONFLICT DO NOTHING;

-- Display summary
SELECT 'Schema alignment complete!' as status;
SELECT 'Added tables:' as info, COUNT(*) as count FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE 'humansa_%';