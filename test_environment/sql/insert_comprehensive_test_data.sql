-- Comprehensive test data for Humansa V2
-- This script ensures all tables have proper test data

-- First ensure clinics have city data
UPDATE humansa_clinic SET city = '北京' WHERE clinic_code IN ('CL001', 'CLINIC002') AND city IS NULL;
UPDATE humansa_clinic SET city = '深圳' WHERE clinic_code IN ('CL002', 'CLINIC001') AND city IS NULL;
UPDATE humansa_clinic SET city = '广州' WHERE clinic_code IN ('CL003', 'CLINIC003') AND city IS NULL;

-- Insert test doctors with diverse specialties and locations
INSERT INTO humansa_doctor (doctor_id, name, specialty, qualifications, experience_years, languages, clinic_code, consultation_fee, expertise, title, bio) VALUES
-- Beijing doctors
('DOC001', '张伟', '骨科', '主任医师，北京协和医学院博士', 15, ARRAY['中文', '英文'], 'CL001', 300.00, '关节置换、脊柱手术、运动损伤', '主任医师', '张伟医生在骨科领域有15年的临床经验，擅长各类骨科手术。'),
('DOC002', '李娜', '儿科', '副主任医师，首都医科大学硕士', 10, ARRAY['中文'], 'CL001', 200.00, '儿童呼吸道疾病、儿童生长发育', '副主任医师', '李娜医生专注于儿童常见病的诊治，深受家长信任。'),
('DOC003', '王强', '内科', '主治医师，复旦大学医学院', 8, ARRAY['中文', '英文'], 'CLINIC002', 150.00, '高血压、糖尿病、慢性病管理', '主治医师', '王强医生在内科慢性病管理方面经验丰富。'),

-- Shenzhen doctors
('DOC004', '刘芳', '妇科', '主任医师，上海交通大学医学院博士', 20, ARRAY['中文', '粤语'], 'CL002', 350.00, '妇科肿瘤、宫腔镜手术', '主任医师', '刘芳医生是妇科专家，在妇科疾病诊治方面造诣深厚。'),
('DOC005', '陈明', '眼科', '副主任医师，中山大学医学院', 12, ARRAY['中文', '英文'], 'CL002', 250.00, '白内障、近视矫正、眼底病', '副主任医师', '陈明医生擅长各类眼科手术和疾病治疗。'),
('DOC006', '赵丽', '皮肤科', '主治医师，浙江大学医学院', 6, ARRAY['中文'], 'CLINIC001', 180.00, '痤疮、湿疹、皮肤美容', '主治医师', '赵丽医生在皮肤病诊治和美容方面有丰富经验。'),

-- Guangzhou doctors
('DOC007', '孙浩', '心内科', '主任医师，华中科技大学同济医学院', 18, ARRAY['中文', '英文'], 'CL003', 400.00, '冠心病、心律失常、心脏介入', '主任医师', '孙浩医生是心血管疾病专家，擅长心脏介入治疗。'),
('DOC008', '周敏', '耳鼻喉科', '副主任医师，中南大学湘雅医学院', 11, ARRAY['中文', '粤语'], 'CL003', 220.00, '鼻炎、咽喉疾病、听力障碍', '副主任医师', '周敏医生在耳鼻喉科疾病诊治方面经验丰富。'),
('DOC009', '吴刚', '神经外科', '主任医师，四川大学华西医学院', 22, ARRAY['中文', '英文'], 'CLINIC003', 500.00, '脑肿瘤、脊髓疾病、神经创伤', '主任医师', '吴刚医生是神经外科专家，手术经验丰富。'),

-- Additional specialists
('DOC010', '郑雪', '中医科', '副主任医师，北京中医药大学', 14, ARRAY['中文'], 'CLINIC003', 280.00, '中医内科、针灸、推拿', '副主任医师', '郑雪医生擅长中医调理和针灸治疗。'),
('DOC011', '林涛', '骨科', '副主任医师，广州医科大学', 13, ARRAY['中文', '粤语'], 'CLINIC003', 260.00, '运动医学、关节镜手术', '副主任医师', '林涛医生专注于运动损伤和关节疾病治疗。'),
('DOC012', '黄晓明', '儿科', '主治医师，深圳大学医学院', 7, ARRAY['中文', '英文'], 'CLINIC001', 170.00, '小儿哮喘、过敏性疾病', '主治医师', '黄晓明医生在儿童呼吸道和过敏性疾病方面有专长。'),
('DOC013', '杨丽华', '妇产科', '主任医师，北京大学医学部', 19, ARRAY['中文', '英文'], 'CLINIC002', 380.00, '产科、高危妊娠、妇科内分泌', '主任医师', '杨丽华医生是妇产科专家，擅长处理高危妊娠。'),
('DOC014', '马建国', '泌尿科', '副主任医师，清华大学医学院', 11, ARRAY['中文'], 'CL001', 240.00, '前列腺疾病、泌尿系结石', '副主任医师', '马建国医生在泌尿系统疾病治疗方面经验丰富。'),
('DOC015', '徐静', '内分泌科', '主治医师，南方医科大学', 9, ARRAY['中文', '粤语'], 'CL002', 190.00, '糖尿病、甲状腺疾病', '主治医师', '徐静医生专注于内分泌疾病的诊治。')
ON CONFLICT (doctor_id) DO UPDATE SET
    name = EXCLUDED.name,
    specialty = EXCLUDED.specialty,
    clinic_code = EXCLUDED.clinic_code,
    expertise = EXCLUDED.expertise,
    qualifications = EXCLUDED.qualifications,
    consultation_fee = EXCLUDED.consultation_fee;

-- Sync doctor_code with doctor_id
UPDATE humansa_doctor SET doctor_code = doctor_id WHERE doctor_code IS NULL;

-- Insert comprehensive schedules for next 14 days
DO $$
DECLARE
    doc RECORD;
    day_offset INTEGER;
    schedule_date DATE;
BEGIN
    -- Clear existing schedules
    DELETE FROM humansa_schedule WHERE shift_date >= CURRENT_DATE;
    
    FOR doc IN SELECT doctor_id, clinic_code FROM humansa_doctor LOOP
        FOR day_offset IN 0..13 LOOP
            schedule_date := CURRENT_DATE + day_offset;
            
            -- Skip Sundays
            IF EXTRACT(DOW FROM schedule_date) != 0 THEN
                -- Morning shift (9:00-12:00)
                INSERT INTO humansa_schedule (doctor_id, doctor_code, clinic_code, shift_date, start_time, end_time, available_slots, booked_slots)
                VALUES (doc.doctor_id, doc.doctor_id, doc.clinic_code, schedule_date, '09:00', '12:00', 12, 
                        CASE WHEN random() < 0.3 THEN floor(random() * 5)::int ELSE 0 END)
                ON CONFLICT (doctor_id, shift_date, start_time) DO NOTHING;
                
                -- Afternoon shift (14:00-17:00) - some doctors only
                IF random() > 0.3 THEN
                    INSERT INTO humansa_schedule (doctor_id, doctor_code, clinic_code, shift_date, start_time, end_time, available_slots, booked_slots)
                    VALUES (doc.doctor_id, doc.doctor_id, doc.clinic_code, schedule_date, '14:00', '17:00', 12,
                            CASE WHEN random() < 0.2 THEN floor(random() * 3)::int ELSE 0 END)
                    ON CONFLICT (doctor_id, shift_date, start_time) DO NOTHING;
                END IF;
                
                -- Evening shift (18:00-20:00) - few doctors
                IF random() > 0.7 THEN
                    INSERT INTO humansa_schedule (doctor_id, doctor_code, clinic_code, shift_date, start_time, end_time, available_slots, booked_slots)
                    VALUES (doc.doctor_id, doc.doctor_id, doc.clinic_code, schedule_date, '18:00', '20:00', 8, 0)
                    ON CONFLICT (doctor_id, shift_date, start_time) DO NOTHING;
                END IF;
            END IF;
        END LOOP;
    END LOOP;
END $$;

-- Insert sample patients
INSERT INTO humansa_patient (patient_id, phone, name, gender, birth_date, email, address, medical_history, allergies) VALUES
('PAT001', '13800138001', '张三', '男', '1978-05-15', 'zhangsan@example.com', '北京市朝阳区', '高血压5年', '花生过敏'),
('PAT002', '13800138002', '李四', '女', '1985-08-20', 'lisi@example.com', '深圳市南山区', '糖尿病3年', '无'),
('PAT003', '13800138003', '王五', '男', '1990-03-10', 'wangwu@example.com', '广州市天河区', '无', '青霉素过敏'),
('PAT004', '13800138004', '赵六', '女', '1995-11-25', 'zhaoliu@example.com', '北京市海淀区', '哮喘', '海鲜过敏'),
('PAT005', '13800138005', '陈七', '男', '2018-06-01', 'chenqi_parent@example.com', '深圳市福田区', '无', '无')
ON CONFLICT (patient_id) DO NOTHING;

-- Insert some appointment history
INSERT INTO humansa_appointment_history (patient_id, doctor_id, appointment_date, appointment_time, status, amount) VALUES
('PAT001', 'DOC001', CURRENT_DATE - 30, '09:30', 'completed', 300.00),
('PAT001', 'DOC003', CURRENT_DATE - 15, '10:00', 'completed', 150.00),
('PAT002', 'DOC004', CURRENT_DATE - 20, '14:30', 'completed', 350.00),
('PAT003', 'DOC007', CURRENT_DATE - 10, '15:00', 'completed', 400.00),
('PAT004', 'DOC002', CURRENT_DATE - 5, '11:00', 'completed', 200.00)
ON CONFLICT DO NOTHING;

-- Verify the data
SELECT 'Doctors by city' as category, city, COUNT(*) as count 
FROM humansa_doctor d
JOIN humansa_clinic c ON d.clinic_code = c.clinic_code
GROUP BY city
UNION ALL
SELECT 'Doctors by specialty' as category, specialty, COUNT(*) as count 
FROM humansa_doctor
GROUP BY specialty
UNION ALL
SELECT 'Total schedules' as category, 'All', COUNT(*) as count 
FROM humansa_schedule WHERE shift_date >= CURRENT_DATE
UNION ALL
SELECT 'Available slots' as category, 'Available', SUM(remaining_slots) as count 
FROM humansa_schedule WHERE shift_date >= CURRENT_DATE
UNION ALL
SELECT 'Patients' as category, 'Total', COUNT(*) as count 
FROM humansa_patient
ORDER BY category;