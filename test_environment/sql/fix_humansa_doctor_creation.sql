-- Create humansa_doctor table with correct foreign key references
CREATE TABLE IF NOT EXISTS humansa_doctor (
    doctor_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    specialty VARCHAR(100),
    qualifications TEXT,
    experience_years INTEGER,
    languages TEXT[],
    clinic_code VARCHAR(50) REFERENCES humansa_clinic(clinic_code),
    department_id INTEGER,
    photo_url TEXT,
    rating DECIMAL(3,2),
    consultation_fee DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create humansa_schedule table
CREATE TABLE IF NOT EXISTS humansa_schedule (
    schedule_id SERIAL PRIMARY KEY,
    doctor_id VARCHAR(50) REFERENCES humansa_doctor(doctor_id),
    clinic_code VARCHAR(50) REFERENCES humansa_clinic(clinic_code),
    shift_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    available_slots INTEGER NOT NULL DEFAULT 0,
    booked_slots INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) DEFAULT 'available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create humansa_appointment_history table if it doesn't exist
CREATE TABLE IF NOT EXISTS humansa_appointment_history (
    appointment_id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50),
    doctor_id VARCHAR(50) REFERENCES humansa_doctor(doctor_id),
    clinic_code VARCHAR(50) REFERENCES humansa_clinic(clinic_code),
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    booking_reference VARCHAR(100) UNIQUE,
    symptoms TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert test doctors
INSERT INTO humansa_doctor (doctor_id, name, specialty, qualifications, experience_years, languages, clinic_code, consultation_fee) VALUES
('DOC001', '张伟医生', '骨科', '主任医师，北京协和医学院博士', 15, ARRAY['中文', '英文'], 'BJ001', 300.00),
('DOC002', '李娜医生', '儿科', '副主任医师，首都医科大学硕士', 10, ARRAY['中文'], 'BJ001', 200.00),
('DOC003', '王强医生', '内科', '主治医师，复旦大学医学院', 8, ARRAY['中文', '英文'], 'BJ002', 150.00),
('DOC004', '刘芳医生', '妇科', '主任医师，上海交通大学医学院博士', 20, ARRAY['中文', '粤语'], 'SH001', 350.00),
('DOC005', '陈明医生', '眼科', '副主任医师，中山大学医学院', 12, ARRAY['中文', '英文'], 'SH001', 250.00),
('DOC006', '赵丽医生', '皮肤科', '主治医师，浙江大学医学院', 6, ARRAY['中文'], 'SH002', 180.00),
('DOC007', '孙浩医生', '心内科', '主任医师，华中科技大学同济医学院', 18, ARRAY['中文', '英文'], 'GZ001', 400.00),
('DOC008', '周敏医生', '耳鼻喉科', '副主任医师，中南大学湘雅医学院', 11, ARRAY['中文', '粤语'], 'GZ001', 220.00),
('DOC009', '吴刚医生', '神经外科', '主任医师，四川大学华西医学院', 22, ARRAY['中文', '英文'], 'SZ001', 500.00),
('DOC010', '郑雪医生', '中医科', '副主任医师，北京中医药大学', 14, ARRAY['中文'], 'SZ001', 280.00)
ON CONFLICT (doctor_id) DO NOTHING;

-- Insert test schedules (next 7 days)
DO $$
DECLARE
    doc RECORD;
    day_offset INTEGER;
    schedule_date DATE;
BEGIN
    FOR doc IN SELECT doctor_id, clinic_code FROM humansa_doctor LOOP
        FOR day_offset IN 0..6 LOOP
            schedule_date := CURRENT_DATE + day_offset;
            
            -- Morning shift
            INSERT INTO humansa_schedule (doctor_id, clinic_code, shift_date, start_time, end_time, available_slots, booked_slots)
            VALUES (doc.doctor_id, doc.clinic_code, schedule_date, '09:00', '12:00', 12, 0)
            ON CONFLICT DO NOTHING;
            
            -- Afternoon shift (skip some days randomly)
            IF day_offset % 3 != 2 THEN
                INSERT INTO humansa_schedule (doctor_id, clinic_code, shift_date, start_time, end_time, available_slots, booked_slots)
                VALUES (doc.doctor_id, doc.clinic_code, schedule_date, '14:00', '17:00', 12, 0)
                ON CONFLICT DO NOTHING;
            END IF;
        END LOOP;
    END LOOP;
END $$;

-- Verify the data
SELECT 'Doctors' as entity, COUNT(*) as count FROM humansa_doctor
UNION ALL
SELECT 'Schedules' as entity, COUNT(*) as count FROM humansa_schedule
UNION ALL
SELECT 'Clinics' as entity, COUNT(*) as count FROM humansa_clinic;