-- Add test doctors for Humansa V2 testing
-- These doctors cover various specialties and cities mentioned in test cases

-- Clear existing test data
DELETE FROM humansa_schedule WHERE doctor_code LIKE 'TEST_%';
DELETE FROM humansa_doctor WHERE doctor_code LIKE 'TEST_%';

-- Add test doctors
INSERT INTO humansa_doctor (doctor_code, name, title, specialty, expertise, experience_years, clinic_code, rating, bio, registration_fee) VALUES
-- Cardiologists (心脏科)
('TEST_001', '张心远', '主任医师', '心脏科', '冠心病、心律失常、高血压', 25, 'CLINIC001', 4.9, '资深心脏病专家，北京大学医学部毕业，擅长心血管疾病诊治', 300),
('TEST_002', '王心明', '副主任医师', '心脏科', '心脏介入手术、心肌病', 18, 'CLINIC002', 4.8, '心脏介入专家，复旦大学医学院博士', 200),

-- General doctors for search tests
('TEST_003', '李医生', '主治医师', '内科', '慢性病管理、健康体检', 12, 'CLINIC001', 4.7, '内科专家，中山大学医学院毕业，擅长慢病管理', 150),
('TEST_004', '王医生', '副主任医师', '全科', '常见病诊治、健康咨询', 15, 'CLINIC003', 4.8, '全科医生，华中科技大学同济医学院毕业', 180),
('TEST_005', '张医生', '主任医师', '中医科', '中医调理、针灸推拿', 20, 'CLINIC002', 4.9, '中医专家，广州中医药大学博士，擅长中医调理', 250),

-- Orthopedists (骨科) for Beijing
('TEST_006', '刘骨科', '主任医师', '骨科', '关节置换、骨折治疗', 28, 'CLINIC002', 4.9, '骨科专家，北京协和医学院毕业，20年以上经验', 350),
('TEST_007', '陈骨医', '主任医师', '骨科', '脊柱外科、运动损伤', 22, 'CLINIC002', 4.8, '脊柱外科专家，首都医科大学博士，20年以上经验', 300),

-- More doctors for various cities
('TEST_008', '赵内科', '副主任医师', '内科', '消化系统疾病、糖尿病', 16, 'CLINIC001', 4.7, '消化内科专家，浙江大学医学院毕业', 200),
('TEST_009', '孙儿科', '主治医师', '儿科', '儿童常见病、生长发育', 10, 'CLINIC001', 4.8, '儿科专家，上海交通大学医学院毕业', 150),
('TEST_010', '周中医', '副主任医师', '中医科', '中医内科、慢病调理', 17, 'CLINIC003', 4.7, '中医内科专家，南京中医药大学毕业', 180);

-- Add availability for next 7 days for key test doctors
DO $$
DECLARE
    i INTEGER;
    doc_code TEXT;
    sched_date DATE;
BEGIN
    -- For each test doctor
    FOR doc_code IN SELECT doctor_code FROM humansa_doctor WHERE doctor_code LIKE 'TEST_%' LOOP
        -- Add shifts for next 7 days
        FOR i IN 0..6 LOOP
            sched_date := CURRENT_DATE + i;
            
            -- Morning shift (9:00-12:00)
            INSERT INTO humansa_schedule (doctor_code, clinic_code, schedule_date, start_time, end_time, is_available)
            VALUES (doc_code, 
                    (SELECT clinic_code FROM humansa_doctor WHERE doctor_code = doc_code),
                    sched_date,
                    '09:00:00',
                    '12:00:00',
                    true);
                    
            -- Afternoon shift (14:00-17:00)
            INSERT INTO humansa_schedule (doctor_code, clinic_code, schedule_date, start_time, end_time, is_available)
            VALUES (doc_code,
                    (SELECT clinic_code FROM humansa_doctor WHERE doctor_code = doc_code),
                    sched_date,
                    '14:00:00',
                    '17:00:00',
                    true);
        END LOOP;
    END LOOP;
END $$;