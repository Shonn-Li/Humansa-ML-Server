-- Fix schema alignment and add test data
-- This aligns with the existing schema structure

-- First, let's add city column to clinic if it doesn't exist
ALTER TABLE humansa_clinic ADD COLUMN IF NOT EXISTS city VARCHAR(50);

-- Drop the tables we created with wrong schema
DROP TABLE IF EXISTS humansa_appointment_history CASCADE;
DROP TABLE IF EXISTS humansa_schedule CASCADE;  
DROP TABLE IF EXISTS humansa_doctor CASCADE;

-- Recreate doctor table with correct foreign key
CREATE TABLE humansa_doctor (
    doctor_code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    title VARCHAR(100),
    specialty VARCHAR(100),
    expertise TEXT,
    experience_years INTEGER,
    clinic_id INTEGER REFERENCES humansa_clinic(id),
    rating DECIMAL(2,1),
    bio TEXT,
    registration_fee INTEGER
);

-- Recreate schedule table with correct foreign key
CREATE TABLE humansa_schedule (
    schedule_id SERIAL PRIMARY KEY,
    doctor_code VARCHAR(10) REFERENCES humansa_doctor(doctor_code),
    clinic_id INTEGER REFERENCES humansa_clinic(id),
    shift_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    remaining_slots INTEGER DEFAULT 10,
    UNIQUE(doctor_code, shift_date, start_time)
);

-- Add constraint
ALTER TABLE humansa_schedule 
ADD CONSTRAINT positive_slots CHECK (remaining_slots >= 0);

-- Add some test clinics if they don't exist
INSERT INTO humansa_clinic (name, address, phone, city, operating_hours) VALUES
('北京和睦家诊所', '北京市朝阳区将台路2号', '010-59277000', '北京', '周一至周日 8:00-20:00'),
('深圳和睦家诊所', '深圳市福田区海田路1033号', '0755-86686888', '深圳', '周一至周日 8:00-20:00'),
('广州和睦家诊所', '广州市天河区林和西路161号', '020-38681888', '广州', '周一至周日 8:00-20:00')
ON CONFLICT DO NOTHING
RETURNING id, name;

-- Get clinic IDs for inserting doctors
-- We'll use a DO block to insert doctors with correct clinic_id
DO $$
DECLARE
    beijing_clinic_id INTEGER;
    shenzhen_clinic_id INTEGER;
    guangzhou_clinic_id INTEGER;
BEGIN
    -- Get clinic IDs
    SELECT id INTO beijing_clinic_id FROM humansa_clinic WHERE city = '北京' LIMIT 1;
    SELECT id INTO shenzhen_clinic_id FROM humansa_clinic WHERE city = '深圳' LIMIT 1;
    SELECT id INTO guangzhou_clinic_id FROM humansa_clinic WHERE city = '广州' LIMIT 1;
    
    -- Insert test doctors
    INSERT INTO humansa_doctor (doctor_code, name, title, specialty, expertise, experience_years, clinic_id, rating, bio, registration_fee) VALUES
    -- Cardiologists
    ('TEST_001', '张心远', '主任医师', '心脏科', '冠心病、心律失常、高血压', 25, beijing_clinic_id, 4.9, '资深心脏病专家，北京大学医学部毕业，擅长心血管疾病诊治', 300),
    ('TEST_002', '王心明', '副主任医师', '心脏科', '心脏介入手术、心肌病', 18, shenzhen_clinic_id, 4.8, '心脏介入专家，复旦大学医学院博士', 200),
    -- General doctors
    ('TEST_003', '李医生', '主治医师', '内科', '慢性病管理、健康体检', 12, beijing_clinic_id, 4.7, '内科专家，中山大学医学院毕业，擅长慢病管理', 150),
    ('TEST_004', '王医生', '副主任医师', '全科', '常见病诊治、健康咨询', 15, guangzhou_clinic_id, 4.8, '全科医生，华中科技大学同济医学院毕业', 180),
    ('TEST_005', '张医生', '主任医师', '中医科', '中医调理、针灸推拿', 20, shenzhen_clinic_id, 4.9, '中医专家，广州中医药大学博士，擅长中医调理', 250),
    -- Orthopedists for Beijing
    ('TEST_006', '刘骨科', '主任医师', '骨科', '关节置换、骨折治疗', 28, beijing_clinic_id, 4.9, '骨科专家，北京协和医学院毕业，20年以上经验', 350),
    ('TEST_007', '陈骨医', '主任医师', '骨科', '脊柱外科、运动损伤', 22, beijing_clinic_id, 4.8, '脊柱外科专家，首都医科大学博士，20年以上经验', 300),
    -- More doctors
    ('TEST_008', '赵内科', '副主任医师', '内科', '消化系统疾病、糖尿病', 16, beijing_clinic_id, 4.7, '消化内科专家，浙江大学医学院毕业', 200),
    ('TEST_009', '孙儿科', '主治医师', '儿科', '儿童常见病、生长发育', 10, beijing_clinic_id, 4.8, '儿科专家，上海交通大学医学院毕业', 150),
    ('TEST_010', '周中医', '副主任医师', '中医科', '中医内科、慢病调理', 17, guangzhou_clinic_id, 4.7, '中医内科专家，南京中医药大学毕业', 180)
    ON CONFLICT (doctor_code) DO NOTHING;
    
    -- Add schedules for doctors
    INSERT INTO humansa_schedule (doctor_code, clinic_id, shift_date, start_time, end_time, remaining_slots)
    SELECT 
        d.doctor_code,
        d.clinic_id,
        CURRENT_DATE + s.day_offset,
        s.start_time,
        s.end_time,
        10
    FROM humansa_doctor d
    CROSS JOIN (
        SELECT generate_series(0, 6) as day_offset, '09:00:00'::time as start_time, '12:00:00'::time as end_time
        UNION ALL
        SELECT generate_series(0, 6) as day_offset, '14:00:00'::time as start_time, '17:00:00'::time as end_time
    ) s
    WHERE d.doctor_code LIKE 'TEST_%'
    ON CONFLICT DO NOTHING;
END $$;

-- Recreate appointment history table with correct schema
CREATE TABLE humansa_appointment_history (
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
CREATE INDEX idx_appointment_patient ON humansa_appointment_history(patient_id);
CREATE INDEX idx_appointment_doctor ON humansa_appointment_history(doctor_code);
CREATE INDEX idx_appointment_date ON humansa_appointment_history(appointment_date);
CREATE INDEX idx_appointment_status ON humansa_appointment_history(status);

-- Add test appointment history
INSERT INTO humansa_appointment_history 
(patient_id, doctor_code, appointment_date, appointment_time, status, amount, notes) 
VALUES
('PAT_test_user_14', 'TEST_001', CURRENT_DATE + INTERVAL '2 days', '09:00:00', 'confirmed', 300, '初诊'),
('PAT_test_user_14', 'TEST_003', CURRENT_DATE - INTERVAL '7 days', '14:00:00', 'completed', 150, '复诊')
ON CONFLICT DO NOTHING;