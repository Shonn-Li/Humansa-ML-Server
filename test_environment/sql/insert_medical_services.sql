-- Insert medical services for each clinic
INSERT INTO humansa_medical_service (service_id, name, description, price, clinic_code, department_id) VALUES
-- Services for CL001 (北京协和医院)
('SVC001', '骨科门诊', '骨科专家门诊服务', 300.00, 'CL001', 1),
('SVC002', 'X光检查', '数字X光拍片检查', 150.00, 'CL001', 1),
('SVC003', '儿科门诊', '儿科专家门诊服务', 200.00, 'CL001', 2),
('SVC004', '血常规检查', '儿童血常规检验', 80.00, 'CL001', 2),

-- Services for CL002 (深圳人民医院)
('SVC005', '妇科门诊', '妇科专家门诊服务', 350.00, 'CL002', 3),
('SVC006', '妇科B超', '妇科超声波检查', 200.00, 'CL002', 3),
('SVC007', '眼科门诊', '眼科专家门诊服务', 250.00, 'CL002', 4),
('SVC008', '视力检查', '综合视力检测', 120.00, 'CL002', 4),

-- Services for CL003 (广州中山医院)
('SVC009', '心内科门诊', '心内科专家门诊', 400.00, 'CL003', 5),
('SVC010', '心电图', '12导联心电图检查', 100.00, 'CL003', 5),
('SVC011', '耳鼻喉科门诊', '耳鼻喉科专家门诊', 220.00, 'CL003', 6),
('SVC012', '听力测试', '专业听力检测', 180.00, 'CL003', 6),

-- Services for CLINIC001 (诺亚新舟深圳健康中心)
('SVC013', '皮肤科门诊', '皮肤科专家门诊', 180.00, 'CLINIC001', 7),
('SVC014', '皮肤镜检查', '皮肤镜检测服务', 150.00, 'CLINIC001', 7),
('SVC015', '神经外科门诊', '神经外科专家门诊', 500.00, 'CLINIC001', 8),
('SVC016', '脑电图', '脑电图检查', 300.00, 'CLINIC001', 8),

-- Services for CLINIC002 (诺亚新舟北京医疗中心)
('SVC017', '内科门诊', '内科专家门诊服务', 150.00, 'CLINIC002', 9),
('SVC018', '肝功能检查', '肝功能全套检验', 120.00, 'CLINIC002', 9),
('SVC019', '妇产科门诊', '妇产科专家门诊', 380.00, 'CLINIC002', 10),
('SVC020', '产前检查', '孕期产前检查套餐', 500.00, 'CLINIC002', 10),

-- Services for CLINIC003 (诺亚新舟广州诊所)
('SVC021', '中医科门诊', '中医专家门诊服务', 280.00, 'CLINIC003', 11),
('SVC022', '针灸治疗', '传统针灸理疗', 200.00, 'CLINIC003', 11),
('SVC023', '拔罐治疗', '传统拔罐理疗', 150.00, 'CLINIC003', 11),
('SVC024', '体检套餐', '基础健康体检套餐', 680.00, 'CLINIC003', 12),
('SVC025', '高端体检', 'VIP全面体检套餐', 1880.00, 'CLINIC003', 12)
ON CONFLICT (service_id) DO UPDATE SET
    name = EXCLUDED.name,
    price = EXCLUDED.price,
    clinic_code = EXCLUDED.clinic_code;

-- Update the service table to have better categorization
UPDATE humansa_service SET category = '门诊服务' WHERE name LIKE '%门诊%';
UPDATE humansa_service SET category = '检查检验' WHERE name LIKE '%检查%' OR name LIKE '%检验%' OR name LIKE '%测试%';
UPDATE humansa_service SET category = '理疗服务' WHERE name LIKE '%治疗%' OR name LIKE '%理疗%';
UPDATE humansa_service SET category = '体检套餐' WHERE name LIKE '%体检%';

-- Verify the data
SELECT 'Medical Services' as entity, COUNT(*) as count FROM humansa_medical_service
UNION ALL
SELECT 'Services by Clinic' as entity, COUNT(DISTINCT clinic_code) as count FROM humansa_medical_service;