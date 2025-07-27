-- Fix Humansa schema issues
-- 1. Drop duplicate table and use consistent naming
-- 2. Add missing columns and tables
-- 3. Fix foreign key constraints

BEGIN;

-- Step 1: Check column existence in humansa_schedule
DO $$
BEGIN
    -- Check if shift_date column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'humansa_schedule' 
        AND column_name = 'shift_date'
    ) THEN
        -- Rename schedule_date to shift_date if it exists
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'humansa_schedule' 
            AND column_name = 'schedule_date'
        ) THEN
            ALTER TABLE humansa_schedule RENAME COLUMN schedule_date TO shift_date;
        ELSE
            -- Add shift_date column if neither exists
            ALTER TABLE humansa_schedule ADD COLUMN shift_date DATE NOT NULL DEFAULT CURRENT_DATE;
        END IF;
    END IF;
    
    -- Ensure remaining_slots column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'humansa_schedule' 
        AND column_name = 'remaining_slots'
    ) THEN
        ALTER TABLE humansa_schedule ADD COLUMN remaining_slots INTEGER DEFAULT 10;
        -- Drop is_available if it exists
        ALTER TABLE humansa_schedule DROP COLUMN IF EXISTS is_available;
    END IF;
END $$;

-- Step 2: Fix clinic table naming (use humansa_clinic, not humansa_clinics)
DO $$
BEGIN
    -- If humansa_clinics exists but humansa_clinic doesn't, rename it
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'humansa_clinics') 
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'humansa_clinic') THEN
        ALTER TABLE humansa_clinics RENAME TO humansa_clinic;
    END IF;
    
    -- If both exist, migrate data from clinics to clinic and drop clinics
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'humansa_clinics') 
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'humansa_clinic') THEN
        -- Copy any missing data
        INSERT INTO humansa_clinic (clinic_code, name, address, phone, city, operating_hours)
        SELECT clinic_code, name, address, phone, city, operating_hours
        FROM humansa_clinics
        WHERE clinic_code NOT IN (SELECT clinic_code FROM humansa_clinic);
        
        -- Drop the duplicate table
        DROP TABLE IF EXISTS humansa_clinics CASCADE;
    END IF;
END $$;

-- Step 3: Add missing columns to humansa_clinic
ALTER TABLE humansa_clinic ADD COLUMN IF NOT EXISTS city VARCHAR(50);
ALTER TABLE humansa_clinic ADD COLUMN IF NOT EXISTS operating_hours TEXT;

-- Step 4: Add schedule_id to humansa_schedule if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'humansa_schedule' 
        AND column_name = 'schedule_id'
    ) THEN
        -- Add serial primary key
        ALTER TABLE humansa_schedule ADD COLUMN schedule_id SERIAL PRIMARY KEY;
    END IF;
END $$;

-- Step 5: Add missing columns to humansa_doctor if they don't exist
ALTER TABLE humansa_doctor ADD COLUMN IF NOT EXISTS specialty VARCHAR(100);
ALTER TABLE humansa_doctor ADD COLUMN IF NOT EXISTS experience_years INTEGER;
ALTER TABLE humansa_doctor ADD COLUMN IF NOT EXISTS rating DECIMAL(3,2);

-- Step 6: Add test clinics if they don't exist
INSERT INTO humansa_clinic (clinic_code, name, address, phone, city, operating_hours) VALUES
('CLINIC001', '北京和睦家诊所', '北京市朝阳区将台路2号', '010-59277000', '北京', '周一至周日 8:00-20:00'),
('CLINIC002', '深圳和睦家诊所', '深圳市福田区海田路1033号', '0755-86686888', '深圳', '周一至周日 8:00-20:00'),
('CLINIC003', '广州和睦家诊所', '广州市天河区林和西路161号', '020-38681888', '广州', '周一至周日 8:00-20:00')
ON CONFLICT (clinic_code) DO UPDATE SET
    name = EXCLUDED.name,
    city = EXCLUDED.city,
    operating_hours = EXCLUDED.operating_hours;

-- Step 7: Update doctors to ensure they have valid clinics
UPDATE humansa_doctor d
SET clinic_code = 'CLINIC001'
WHERE NOT EXISTS (SELECT 1 FROM humansa_clinic c WHERE c.clinic_code = d.clinic_code)
AND d.name LIKE '%北京%' OR d.bio LIKE '%北京%';

UPDATE humansa_doctor d
SET clinic_code = 'CLINIC002'
WHERE NOT EXISTS (SELECT 1 FROM humansa_clinic c WHERE c.clinic_code = d.clinic_code)
AND (d.name LIKE '%深圳%' OR d.bio LIKE '%深圳%' OR d.clinic_code IN ('H4', 'H6', 'H7'));

UPDATE humansa_doctor d
SET clinic_code = 'CLINIC003'
WHERE NOT EXISTS (SELECT 1 FROM humansa_clinic c WHERE c.clinic_code = d.clinic_code);

-- Step 8: Create schedule entries for test doctors
INSERT INTO humansa_schedule (doctor_code, clinic_code, shift_date, start_time, end_time, remaining_slots)
SELECT 
    d.doctor_code,
    d.clinic_code,
    CURRENT_DATE + (day_offset || ' days')::INTERVAL,
    CASE 
        WHEN shift_type = 'morning' THEN '09:00:00'::TIME
        ELSE '14:00:00'::TIME
    END,
    CASE 
        WHEN shift_type = 'morning' THEN '12:00:00'::TIME
        ELSE '17:00:00'::TIME
    END,
    10
FROM humansa_doctor d
CROSS JOIN (VALUES (0), (1), (2), (3), (4), (5), (6)) AS days(day_offset)
CROSS JOIN (VALUES ('morning'), ('afternoon')) AS shifts(shift_type)
WHERE d.doctor_code LIKE 'TEST_%'
ON CONFLICT DO NOTHING;

-- Step 9: Create department table
CREATE TABLE IF NOT EXISTS humansa_department (
    dept_id VARCHAR(20) PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    clinic_code VARCHAR(10) REFERENCES humansa_clinic(clinic_code),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 10: Add departments
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

-- Step 11: Add dept_id to doctors
ALTER TABLE humansa_doctor ADD COLUMN IF NOT EXISTS dept_id VARCHAR(20);

-- Update doctors with appropriate departments
UPDATE humansa_doctor SET dept_id = 'DEPT001' WHERE specialty = '心脏科' AND clinic_code = 'CLINIC001';
UPDATE humansa_doctor SET dept_id = 'DEPT002' WHERE specialty = '骨科' AND clinic_code = 'CLINIC001';
UPDATE humansa_doctor SET dept_id = 'DEPT003' WHERE specialty = '内科' AND clinic_code = 'CLINIC001';
UPDATE humansa_doctor SET dept_id = 'DEPT004' WHERE specialty = '儿科' AND clinic_code = 'CLINIC001';
UPDATE humansa_doctor SET dept_id = 'DEPT005' WHERE specialty = '中医科' AND clinic_code = 'CLINIC001';
UPDATE humansa_doctor SET dept_id = 'DEPT006' WHERE specialty = '心脏科' AND clinic_code = 'CLINIC002';
UPDATE humansa_doctor SET dept_id = 'DEPT007' WHERE specialty = '骨科' AND clinic_code = 'CLINIC002';
UPDATE humansa_doctor SET dept_id = 'DEPT008' WHERE specialty = '内科' AND clinic_code = 'CLINIC002';

-- Step 12: Create patient table
CREATE TABLE IF NOT EXISTS humansa_patient (
    patient_id VARCHAR(50) PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    email VARCHAR(100),
    id_number VARCHAR(50),
    gender VARCHAR(10),
    birth_date DATE,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 13: Create appointment history
CREATE TABLE IF NOT EXISTS humansa_appointment_history (
    appointment_id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES humansa_patient(patient_id),
    doctor_code VARCHAR(10) REFERENCES humansa_doctor(doctor_code),
    schedule_id INTEGER,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(50) DEFAULT 'confirmed',
    booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    amount DECIMAL(10,2)
);

-- Step 14: Add test patients
INSERT INTO humansa_patient (patient_id, phone, name, gender, birth_date, address) VALUES
('PAT001', '13800138000', '李明', '男', '1990-05-15', '北京市朝阳区'),
('PAT002', '13900139000', '王芳', '女', '1985-08-20', '上海市浦东新区'),
('PAT003', '13700137000', '张三', '男', '1978-03-10', '北京市海淀区')
ON CONFLICT (patient_id) DO NOTHING;

-- Add some appointment history
INSERT INTO humansa_appointment_history (patient_id, doctor_code, appointment_date, appointment_time, status, amount) 
SELECT 'PAT001', 'TEST_001', CURRENT_DATE - INTERVAL '7 days', '09:00:00', 'completed', 300
WHERE EXISTS (SELECT 1 FROM humansa_doctor WHERE doctor_code = 'TEST_001')
ON CONFLICT DO NOTHING;

COMMIT;

-- Display summary
SELECT 'Schema fixes applied successfully!' as status;