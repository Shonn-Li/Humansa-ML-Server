-- Insert test data with correct structure

-- Insert clinics
INSERT INTO humansa_clinic (clinic_code, name, address, phone) VALUES
('CL001', '北京协和医院', '北京市东城区帅府园1号', '010-69156114'),
('CL002', '深圳人民医院', '深圳市罗湖区东门北路1017号', '0755-25533018'),
('CL003', '广州中山医院', '广州市越秀区中山二路106号', '020-87755766')
ON CONFLICT (clinic_code) DO NOTHING;

-- Insert doctors
INSERT INTO humansa_doctor (doctor_code, clinic_code, name, title, expertise, bio, registration_fee) VALUES
('DR001', 'CL001', '王医生', '主任医师', '心内科', '擅长心血管疾病治疗，20年临床经验', 300.00),
('DR002', 'CL001', '李医生', '副主任医师', '骨科', '擅长骨科手术，15年临床经验', 200.00),
('DR003', 'CL002', '张医生', '主治医师', '心脏科', '擅长心脏疾病诊治', 150.00),
('DR004', 'CL003', '刘医生', '主任医师', '神经内科', '擅长神经系统疾病', 250.00)
ON CONFLICT (doctor_code) DO NOTHING;

-- Check schedule table columns and insert accordingly
DO $$
DECLARE
    col_exists boolean;
BEGIN
    -- Check if schedule_date column exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'humansa_schedule' AND column_name = 'schedule_date'
    ) INTO col_exists;
    
    IF col_exists THEN
        INSERT INTO humansa_schedule (doctor_code, clinic_code, schedule_date, start_time, end_time, is_available) VALUES
        ('DR001', 'CL001', CURRENT_DATE + INTERVAL '1 day', '09:00', '10:00', true),
        ('DR001', 'CL001', CURRENT_DATE + INTERVAL '1 day', '10:00', '11:00', true),
        ('DR001', 'CL001', CURRENT_DATE + INTERVAL '2 days', '14:00', '15:00', true),
        ('DR002', 'CL001', CURRENT_DATE + INTERVAL '1 day', '11:00', '12:00', true),
        ('DR003', 'CL002', CURRENT_DATE + INTERVAL '3 days', '15:00', '16:00', true)
        ON CONFLICT DO NOTHING;
    END IF;
END $$;

-- Insert medical services
INSERT INTO humansa_medical_service (clinic_code, service_name, service_type, description, price_range_min, price_range_max) VALUES
('CL001', '肝功能检查', '检验科', '全面肝功能检测', 200.00, 300.00),
('CL001', '核磁共振', '影像科', 'MRI全身扫描', 1000.00, 1500.00),
('CL002', '体检套餐A', '体检', '基础体检项目', 500.00, 600.00),
('CL003', '体检套餐B', '体检', '全面体检项目', 900.00, 1200.00)
ON CONFLICT DO NOTHING;