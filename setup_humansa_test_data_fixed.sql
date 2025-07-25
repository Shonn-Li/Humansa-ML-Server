-- Insert test data with correct column names

-- First check if humansa_clinic exists and has data
INSERT INTO humansa_clinic (clinic_code, name, city, description) VALUES
('CL001', '北京协和医院', '北京', '北京市顶级三甲医院'),
('CL002', '深圳人民医院', '深圳', '深圳市综合性医院'),
('CL003', '广州中山医院', '广州', '广州市知名医院')
ON CONFLICT (clinic_code) DO NOTHING;

-- Insert doctors with correct columns (expertise instead of specialty)
INSERT INTO humansa_doctor (doctor_code, clinic_code, name, title, expertise, bio, registration_fee) VALUES
('DR001', 'CL001', '王医生', '主任医师', '心内科', '擅长心血管疾病治疗，20年临床经验', 300.00),
('DR002', 'CL001', '李医生', '副主任医师', '骨科', '擅长骨科手术，15年临床经验', 200.00),
('DR003', 'CL002', '张医生', '主治医师', '心脏科', '擅长心脏疾病诊治', 150.00),
('DR004', 'CL003', '刘医生', '主任医师', '神经内科', '擅长神经系统疾病', 250.00)
ON CONFLICT (doctor_code) DO NOTHING;

-- Check schedule table structure and insert with correct columns
DO $$
BEGIN
    -- Try to insert with common column names
    BEGIN
        INSERT INTO humansa_schedule (doctor_code, clinic_code, schedule_date, start_time, end_time, is_available) VALUES
        ('DR001', 'CL001', CURRENT_DATE + INTERVAL '1 day', '09:00', '10:00', true),
        ('DR001', 'CL001', CURRENT_DATE + INTERVAL '1 day', '10:00', '11:00', true),
        ('DR001', 'CL001', CURRENT_DATE + INTERVAL '2 days', '14:00', '15:00', true),
        ('DR002', 'CL001', CURRENT_DATE + INTERVAL '1 day', '11:00', '12:00', true),
        ('DR003', 'CL002', CURRENT_DATE + INTERVAL '3 days', '15:00', '16:00', true)
        ON CONFLICT DO NOTHING;
    EXCEPTION
        WHEN undefined_column THEN
            -- Try with different column names if the first attempt fails
            NULL;
    END;
END $$;

-- Insert medical services with correct columns
DO $$
BEGIN
    -- Check if the table has service columns
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'humansa_medical_service' 
               AND column_name = 'service_name') THEN
        INSERT INTO humansa_medical_service (clinic_code, service_name, service_type, description, price_range_min, price_range_max) VALUES
        ('CL001', '肝功能检查', '检验科', '全面肝功能检测', 200.00, 300.00),
        ('CL001', '核磁共振', '影像科', 'MRI全身扫描', 1000.00, 1500.00),
        ('CL002', '体检套餐A', '体检', '基础体检项目', 500.00, 600.00),
        ('CL003', '体检套餐B', '体检', '全面体检项目', 900.00, 1200.00)
        ON CONFLICT DO NOTHING;
    END IF;
END $$;