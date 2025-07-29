-- Insert test doctors with correct clinic codes
INSERT INTO humansa_doctor (doctor_id, name, specialty, qualifications, experience_years, languages, clinic_code, consultation_fee) VALUES
('DOC001', '张伟医生', '骨科', '主任医师，北京协和医学院博士', 15, ARRAY['中文', '英文'], 'CL001', 300.00),
('DOC002', '李娜医生', '儿科', '副主任医师，首都医科大学硕士', 10, ARRAY['中文'], 'CL001', 200.00),
('DOC003', '王强医生', '内科', '主治医师，复旦大学医学院', 8, ARRAY['中文', '英文'], 'CLINIC002', 150.00),
('DOC004', '刘芳医生', '妇科', '主任医师，上海交通大学医学院博士', 20, ARRAY['中文', '粤语'], 'CL002', 350.00),
('DOC005', '陈明医生', '眼科', '副主任医师，中山大学医学院', 12, ARRAY['中文', '英文'], 'CL002', 250.00),
('DOC006', '赵丽医生', '皮肤科', '主治医师，浙江大学医学院', 6, ARRAY['中文'], 'CLINIC001', 180.00),
('DOC007', '孙浩医生', '心内科', '主任医师，华中科技大学同济医学院', 18, ARRAY['中文', '英文'], 'CL003', 400.00),
('DOC008', '周敏医生', '耳鼻喉科', '副主任医师，中南大学湘雅医学院', 11, ARRAY['中文', '粤语'], 'CL003', 220.00),
('DOC009', '吴刚医生', '神经外科', '主任医师，四川大学华西医学院', 22, ARRAY['中文', '英文'], 'CLINIC001', 500.00),
('DOC010', '郑雪医生', '中医科', '副主任医师，北京中医药大学', 14, ARRAY['中文'], 'CLINIC003', 280.00),
-- More doctors for comprehensive testing
('DOC011', '林涛医生', '骨科', '副主任医师，广州医科大学', 13, ARRAY['中文', '粤语'], 'CLINIC003', 260.00),
('DOC012', '黄晓明医生', '儿科', '主治医师，深圳大学医学院', 7, ARRAY['中文', '英文'], 'CLINIC001', 170.00),
('DOC013', '杨丽华医生', '妇产科', '主任医师，北京大学医学部', 19, ARRAY['中文', '英文'], 'CLINIC002', 380.00),
('DOC014', '马建国医生', '泌尿科', '副主任医师，清华大学医学院', 11, ARRAY['中文'], 'CL001', 240.00),
('DOC015', '徐静医生', '内分泌科', '主治医师，南方医科大学', 9, ARRAY['中文', '粤语'], 'CL002', 190.00)
ON CONFLICT (doctor_id) DO UPDATE SET
    name = EXCLUDED.name,
    specialty = EXCLUDED.specialty,
    clinic_code = EXCLUDED.clinic_code;

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

-- Update clinic cities for better testing
UPDATE humansa_clinic SET city = '北京' WHERE clinic_code IN ('CL001', 'CLINIC002');
UPDATE humansa_clinic SET city = '深圳' WHERE clinic_code IN ('CL002', 'CLINIC001');
UPDATE humansa_clinic SET city = '广州' WHERE clinic_code IN ('CL003', 'CLINIC003');

-- Verify the data
SELECT 'Doctors' as entity, COUNT(*) as count FROM humansa_doctor
UNION ALL
SELECT 'Schedules' as entity, COUNT(*) as count FROM humansa_schedule
UNION ALL
SELECT 'Clinics with city' as entity, COUNT(*) as count FROM humansa_clinic WHERE city IS NOT NULL;