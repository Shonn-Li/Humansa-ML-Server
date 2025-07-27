-- Humansa Test Data for YouWoAI ML Server
-- Based on system prompt data with updated dates
-- All appointments are set to future dates (2 days from now onwards)

-- Create Humansa-specific tables matching the expected schema

-- Clinics table (matches humansa_clinics)
CREATE TABLE IF NOT EXISTS humansa_clinics (
    clinic_code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address TEXT,
    phone VARCHAR(20),
    city VARCHAR(50),
    operating_hours TEXT
);

-- Doctors table (matches humansa_doctor)
CREATE TABLE IF NOT EXISTS humansa_doctor (
    doctor_code VARCHAR(10) PRIMARY KEY,
    clinic_code VARCHAR(10) REFERENCES humansa_clinics(clinic_code),
    name VARCHAR(100) NOT NULL,
    title VARCHAR(100),
    expertise TEXT,
    bio TEXT,
    registration_fee INTEGER
);

-- Doctor schedules (matches humansa_schedule)
CREATE TABLE IF NOT EXISTS humansa_schedule (
    schedule_id SERIAL PRIMARY KEY,
    doctor_code VARCHAR(10) REFERENCES humansa_doctor(doctor_code),
    clinic_code VARCHAR(10) REFERENCES humansa_clinics(clinic_code),
    shift_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    remaining_slots INTEGER DEFAULT 10,
    UNIQUE(doctor_code, shift_date, start_time)
);

-- Medical services (matches humansa_medical_service)
CREATE TABLE IF NOT EXISTS humansa_medical_service (
    service_code VARCHAR(20) PRIMARY KEY,
    clinic_code VARCHAR(10) REFERENCES humansa_clinics(clinic_code),
    name VARCHAR(200) NOT NULL,
    price DECIMAL(10,2),
    description TEXT,
    department VARCHAR(100)
);

-- Service items (matches humansa_service)
CREATE TABLE IF NOT EXISTS humansa_service (
    service_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    department VARCHAR(100),
    price DECIMAL(10,2),
    tags TEXT,
    description TEXT
);

-- Appointments (booked)
CREATE TABLE IF NOT EXISTS humansa_appointments (
    appointment_id SERIAL PRIMARY KEY,
    schedule_id INTEGER REFERENCES humansa_schedule(schedule_id),
    patient_name VARCHAR(100),
    patient_phone VARCHAR(20),
    appointment_time TIME,
    status VARCHAR(50) DEFAULT 'confirmed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Clear existing data
TRUNCATE TABLE humansa_appointments CASCADE;
TRUNCATE TABLE humansa_schedule CASCADE;
TRUNCATE TABLE humansa_medical_service CASCADE;
TRUNCATE TABLE humansa_service CASCADE;
TRUNCATE TABLE humansa_doctor CASCADE;
TRUNCATE TABLE humansa_clinics CASCADE;

-- Insert Clinics
INSERT INTO humansa_clinics (clinic_code, name, address, phone, city) VALUES
('H1', '北京诊所', '北京市朝阳区国贸CBD中心', '010-10000000', '北京'),
('H2', '上海诊所', '上海市浦东新区陆家嘴金融区', '021-20000000', '上海'),
('H3', '广州诊所', '广州市天河区珠江新城CBD', '020-30000000', '广州'),
('H4', '深圳诊所', '深圳市福田区中心区', '0755-40000000', '深圳'),
('H5', '杭州诊所', '杭州市西湖区文三路', '0571-50000000', '杭州'),
('H6', '南京诊所', '南京市建邺区河西新城', '025-60000000', '南京'),
('H7', '天津诊所', '天津市和平区小白楼商务区', '022-70000000', '天津'),
('H8', '苏州诊所', '苏州市工业园区金鸡湖商务区', '0512-80000000', '苏州'),
('H9', '成都诊所', '成都市锦江区春熙路商圈', '028-90000000', '成都'),
('H10', '重庆诊所', '重庆市渝中区解放碑商务区', '023-10000001', '重庆'),
('H11', '武汉诊所', '武汉市武昌区中南路金融街', '027-11000000', '武汉'),
('H12', '西安诊所', '西安市雁塔区高新技术开发区', '029-12000000', '西安'),
('H13', '长沙诊所', '长沙市芙蓉区五一广场商务区', '0731-13000000', '长沙'),
('H14', '青岛诊所', '青岛市市南区香港中路金融区', '0532-14000000', '青岛'),
('H15', '宁波诊所', '宁波市海曙区天一商务区', '0574-15000000', '宁波');

-- Insert Doctors
INSERT INTO humansa_doctor (doctor_code, name, title, expertise, bio, registration_fee, clinic_code) VALUES
('D1', '张三', '主治医师', '心肺复苏、基础生命支持、急危重症处理、高血压、糖尿病等', '中国医科大学硕士；10年内科临床；前第一人民医院主治；多次核心期刊论文', 500, 'H1'),
('D2', '李四', '儿科副主任医师', '儿科急救、新生儿及神经系统疾病、儿科疑难、新生儿重症监护', '北大医学士；协和/北大第一临床进修；38年儿科；多次科技奖及核心期刊发表', 600, 'H2'),
('D3', '王五', '主治医师', '消化/心血管/呼吸/神经内分泌全科；慢病全周期及家庭健康管理', '三甲临床及带敀10余年；健康管理经验丰富；多次学术奖项', 400, 'H3'),
('D4', '赵六', '副主任医师', '骨科创伤、关节置换、脊柱外科、运动医学、康复治疗', '上海交大医学院博士；15年骨科临床；前华山医院副主任；国际骨科学会会员', 800, 'H4'),
('D5', '陈七', '主任医师', '妇产科、不孕不育、产前诊断、妇科肿瘤、微创手术', '复旦大学医学院博士；25年妇产科临床；前妇产科医院主任；多项国家级科研项目', 1000, 'H5'),
('D6', '刘八', '副主任医师', '心血管内科、冠心病、高血压、心律失常、心力衰竭治疗', '中山大学医学院硕士；18年心内科临床；前中山医院副主任；心血管介入资质', 750, 'H6'),
('D7', '吴九', '主任医师', '神经外科、脑肿瘤、颅脑外伤、脑血管疾病、显微神经外科', '北京医科大学博士；20年神经外科临床；前天坛医院主任；神经外科专业委员会委员', 1200, 'H7'),
('D8', '孙十', '副主任医师', '眼科、白内障、青光眼、眼底病、屈光不正、眼整形', '中山大学眼科中心硕士；12年眼科临床；前中山眼科中心副主任；眼科学会会员', 650, 'H8'),
('D9', '周十一', '主治医师', '皮肤性病科、湿疹皮炎、银屑病、性病诊疗、美容皮肤科', '华西医科大学硕士；8年皮肤科临床；前华西医院皮肤科主治；皮肤病学会会员', 450, 'H9'),
('D10', '郑十二', '副主任医师', '耳鼻喉科、鼻窦炎、中耳炎、咽喉疾病、头颈肿瘤、听力重建', '同济医科大学硕士；16年耳鼻喉科临床；前同济医院副主任；耳鼻喉科学会委员', 700, 'H10'),
('D11', '王十三', '主任医师', '消化内科、胃肠疾病、肝胆疾病、内镜诊疗、消化道肿瘤', '北京协和医学院博士；22年消化内科临床；前协和医院主任；消化内镜学会专家', 900, 'H11'),
('D12', '李十四', '副主任医师', '泌尿外科、前列腺疾病、泌尿系肿瘤、泌尿系结石、男科疾病', '四川大学华西医学院硕士；14年泌尿外科临床；前华西医院副主任；泌尿外科学会会员', 680, 'H12'),
('D13', '张十五', '主治医师', '呼吸内科、哮喘、慢阻肺、肺部感染、肺癌筛查、睡眠呼吸疾病', '中南大学湘雅医学院硕士；9年呼吸内科临床；前湘雅医院主治；呼吸病学会会员', 520, 'H13'),
('D14', '黄十六', '副主任医师', '内分泌科、糖尿病、甲状腺疾病、肥胖症、骨质疏松、代谢综合征', '中山大学医学院博士；17年内分泌科临床；前中山医院副主任；内分泌学会专家', 750, 'H14'),
('D15', '刘十七', '主任医师', '肿瘤内科、化疗、靶向治疗、免疫治疗、肿瘤筛查、姑息治疗', '复旦大学肿瘤学院博士；23年肿瘤内科临床；前肿瘤医院主任；肿瘤学会常委', 1100, 'H15');

-- Insert Doctor Schedules (Future dates starting from 2 days from now)
-- Using dynamic date calculation
INSERT INTO humansa_schedule (doctor_code, clinic_code, shift_date, start_time, end_time, remaining_slots)
SELECT 
    doctor_code,
    clinic_code,
    CURRENT_DATE + INTERVAL '2 days' + (day_offset || ' days')::INTERVAL as shift_date,
    start_time::TIME,
    end_time::TIME,
    remaining_slots
FROM (
    VALUES
    -- D1 schedules
    ('D1', 'H1', 0, '09:00', '12:00', 6),
    ('D1', 'H1', 3, '14:00', '17:00', 7),
    ('D1', 'H1', 8, '09:00', '12:00', 5),
    ('D1', 'H1', 13, '14:00', '17:00', 8),
    -- D2 schedules
    ('D2', 'H2', 0, '08:30', '11:30', 7),
    ('D2', 'H2', 4, '13:30', '16:30', 6),
    ('D2', 'H2', 9, '08:30', '11:30', 7),
    ('D2', 'H2', 14, '13:30', '16:30', 9),
    -- D3 schedules
    ('D3', 'H3', 0, '10:00', '13:00', 7),
    ('D3', 'H3', 3, '15:00', '18:00', 8),
    ('D3', 'H3', 8, '10:00', '13:00', 6),
    ('D3', 'H3', 13, '15:00', '18:00', 8),
    -- D4 schedules (extra slots)
    ('D4', 'H4', 0, '09:30', '12:30', 5),
    ('D4', 'H4', 4, '14:30', '17:30', 4),
    ('D4', 'H4', 7, '14:30', '17:30', 8),
    ('D4', 'H4', 8, '09:30', '12:30', 4),
    ('D4', 'H4', 9, '09:30', '12:30', 5),
    ('D4', 'H4', 10, '14:30', '17:30', 7),
    ('D4', 'H4', 11, '09:30', '12:30', 3),
    ('D4', 'H4', 13, '09:30', '12:30', 6),
    ('D4', 'H4', 14, '14:30', '17:30', 8),
    -- D5 schedules (many slots)
    ('D5', 'H5', 0, '08:00', '11:00', 4),
    ('D5', 'H5', 1, '13:00', '16:00', 6),
    ('D5', 'H5', 2, '08:00', '11:00', 5),
    ('D5', 'H5', 3, '08:00', '11:00', 4),
    ('D5', 'H5', 4, '13:00', '16:00', 7),
    ('D5', 'H5', 6, '08:00', '11:00', 5),
    ('D5', 'H5', 7, '13:00', '16:00', 6),
    ('D5', 'H5', 8, '08:00', '11:00', 4),
    ('D5', 'H5', 9, '13:00', '16:00', 5),
    ('D5', 'H5', 10, '08:00', '11:00', 6),
    ('D5', 'H5', 11, '13:00', '16:00', 4),
    ('D5', 'H5', 13, '08:00', '11:00', 5),
    ('D5', 'H5', 14, '13:00', '16:00', 7),
    -- D6 schedules
    ('D6', 'H6', 0, '10:30', '13:30', 6),
    ('D6', 'H6', 1, '15:30', '18:30', 8),
    ('D6', 'H6', 2, '10:30', '13:30', 5),
    ('D6', 'H6', 3, '10:30', '13:30', 7),
    ('D6', 'H6', 4, '15:30', '18:30', 6),
    ('D6', 'H6', 6, '10:30', '13:30', 8),
    ('D6', 'H6', 7, '15:30', '18:30', 9),
    ('D6', 'H6', 8, '10:30', '13:30', 5),
    ('D6', 'H6', 9, '15:30', '18:30', 7),
    ('D6', 'H6', 10, '10:30', '13:30', 6),
    ('D6', 'H6', 11, '10:30', '13:30', 4),
    ('D6', 'H6', 13, '10:30', '13:30', 8),
    ('D6', 'H6', 14, '15:30', '18:30', 9),
    -- D7 schedules
    ('D7', 'H7', 0, '09:00', '12:00', 5),
    ('D7', 'H7', 4, '14:00', '17:00', 6),
    ('D7', 'H7', 9, '09:00', '12:00', 5),
    ('D7', 'H7', 14, '14:00', '17:00', 8),
    -- D8 schedules
    ('D8', 'H8', 0, '08:30', '11:30', 4),
    ('D8', 'H8', 3, '13:30', '16:30', 7),
    ('D8', 'H8', 8, '08:30', '11:30', 5),
    ('D8', 'H8', 13, '13:30', '16:30', 6),
    -- D9 schedules
    ('D9', 'H9', 0, '10:00', '13:00', 6),
    ('D9', 'H9', 4, '15:00', '18:00', 5),
    ('D9', 'H9', 9, '10:00', '13:00', 7),
    ('D9', 'H9', 14, '15:00', '18:00', 8),
    -- D10 schedules
    ('D10', 'H10', 1, '09:30', '12:30', 5),
    ('D10', 'H10', 6, '14:30', '17:30', 7),
    ('D10', 'H10', 10, '09:30', '12:30', 4),
    -- D11 schedules
    ('D11', 'H11', 1, '08:00', '11:00', 4),
    ('D11', 'H11', 7, '13:00', '16:00', 6),
    ('D11', 'H11', 11, '08:00', '11:00', 5),
    -- D12 schedules
    ('D12', 'H12', 1, '10:30', '13:30', 5),
    ('D12', 'H12', 6, '15:30', '18:30', 7),
    ('D12', 'H12', 10, '10:30', '13:30', 6),
    -- D13 schedules
    ('D13', 'H13', 2, '09:00', '12:00', 4),
    ('D13', 'H13', 7, '14:00', '17:00', 5),
    ('D13', 'H13', 11, '09:00', '12:00', 6),
    -- D14 schedules
    ('D14', 'H14', 2, '08:30', '11:30', 5),
    ('D14', 'H14', 6, '13:30', '16:30', 6),
    ('D14', 'H14', 10, '08:30', '11:30', 4)
) AS schedule_data(doctor_code, clinic_code, day_offset, start_time, end_time, remaining_slots);

-- Insert Service Items (humansa_service table)
INSERT INTO humansa_service (service_id, name, department, price, tags, description) VALUES
-- 检查项目
('ITEM1', '肝功三项', '体检中心', 28.50, NULL, '检测肝功能指标'),
('ITEM2', '肾功六项', '体检中心', 47.00, NULL, '检测肾功能指标'),
('ITEM3', '血常规', '体检中心', 40.00, NULL, '血液常规检查'),
('ITEM4', '心电图', '体检中心', 60.00, NULL, '心脏电生理检查'),
('ITEM5', '胸部X光', 120.00, '胸部影像学检查', 'H1/H3/H4', '体检中心', NULL),
('ITEM6', '腹部B超', 180.00, '腹部超声检查', 'H2/H3/H4', '体检中心', NULL),
('ITEM7', '血糖检测', 25.00, '血糖水平检测', 'H1/H2/H3/H4', '体检中心', NULL),
('ITEM8', '血脂四项', 85.00, '血脂全面检查', 'H1/H2/H3/H4', '体检中心', NULL),
('ITEM9', '甲状腺功能', 150.00, '甲状腺激素检测', 'H1/H3/H4', '体检中心', NULL),
('ITEM10', '维生素D', 90.00, '维生素D水平检测', 'H2/H3/H4', '体检中心', NULL),
('ITEM11', '乙肝五项', 65.00, '乙肝病毒标志物检测', 'H1/H2/H3/H4', '体检中心', NULL),
('ITEM12', '尿常规', 30.00, '尿液常规检查', 'H1/H2/H3/H4', '体检中心', NULL),
('ITEM13', '肿瘤标志物', 320.00, '癌症筛查标志物', 'H1/H3/H4', '体检中心', NULL),
('ITEM14', '骨密度检测', 200.00, '骨质疏松筛查', 'H2/H4/H5', '体检中心', NULL),
('ITEM15', '眼底检查', 150.00, '眼底病变筛查', 'H1/H2/H5', '体检中心', NULL),
('ITEM16', '颈动脉超声', 280.00, '颈动脉血管检查', 'H3/H4/H5', '体检中心', NULL),
('ITEM17', '肺功能检测', 160.00, '肺部功能评估', 'H1/H4/H5', '体检中心', NULL),
('ITEM18', '过敏原检测', 450.00, '过敏原筛查', 'H2/H3/H5', '体检中心', NULL),
('ITEM19', '幽门螺杆菌检测', 80.00, '胃部病菌检查', 'H1/H2/H3/H5', '体检中心', NULL),
('ITEM20', '前列腺特异抗原', 120.00, '前列腺健康筛查', 'H1/H3/H4/H5', '体检中心', NULL),
('ITEM21', '女性激素六项', 280.00, '女性内分泌检查', 'H2/H3/H4/H6', '体检中心', NULL),
('ITEM22', '心脏彩超', 380.00, '心脏结构功能检查', 'H1/H4/H5/H6', '体检中心', NULL),
('ITEM23', '脑部MRI', 1200.00, '脑部磁共振检查', 'H4/H5/H6', '体检中心', NULL),
('ITEM24', '全身CT', 2800.00, '全身影像学检查', 'H5/H6', '体检中心', NULL),
('ITEM25', '基因检测', 3500.00, '遗传风险评估', 'H6', '体检中心', NULL),
-- 体检套餐
('PKG1', '无痛胃肠镜检查（不含息肉摘除及病理）', 5440.00, '舒适无痛、精准清晰、省时省心、名医亲诊', '全部诊所', '体检中心', '限时折扣'),
('PKG2', '减重瘦身套餐内科医生咨询及建议', 200.00, '专家一对一解读报告', '全部诊所', '体检中心', NULL),
('PKG3', '启航体检套餐', 1180.00, '肺部低剂量螺旋CT、子宫附件/前列腺彩超、甲状腺/腹部彩超', '全部诊所', '体检中心', '限时折扣'),
('PKG4', '甲状腺超声', 268.00, '精准度高、非侵入性检查、助力早期发现及治疗', '全部诊所', '体检中心', '限时折扣'),
('PKG5', '胃部专项检查（幽门螺旋杆菌检测 + 专家报告）', 745.00, '幽门螺旋杆菌检测（C13呼气试验）+ 专家会诊及解读报告', '全部诊所', '体检中心', NULL),
('PKG6', '血脂四项健康评估套餐（每人限拍1份）', 159.00, NULL, '全部诊所', '体检中心', '限时折扣'),
('PKG7', '优享体检套餐', 4864.00, '专家一对一解读、肺部低剂量螺旋CT、冠脉钙化积分CT', '全部诊所', '体检中心', '限时折扣'),
('PKG8', '悦享体检套餐', 2624.00, '专家一对一、幽门螺旋杆菌（C13）、肿瘤多基因甲基化、低剂量螺旋CT、乳腺彩超', '全部诊所', '体检中心', '限时折扣');

-- Insert Medical Services (humansa_medical_service table)
INSERT INTO humansa_medical_service (service_code, clinic_code, name, price, description, department) VALUES
-- Skin care services
('MED1', 'H1', '半岛黄金版超声炮下颌缘提升', 3499.00, '快乐暑期', '皮肤科'),
('MED2', 'H2', '光子嫩肤 (DPL/BBL) + 化学焕肤（果酸/水杨酸）', 6599.00, '全面部3次套餐，赠医用修复面膜', '皮肤科'),
('MED3', 'H3', '夏日天鹅颈套餐：嗨体祛颈纹1.5 ml + 嗨体水光2.5 ml + 黑金超光子颈部 + 499可换面部光子', 1980.00, '快乐暑期', '皮肤科'),
('MED4', 'H4', '夏日净透套餐：化学焕肤全面部（果酸/水杨酸） + 护理舒敏治疗 + 小气泡深层清洁', 699.00, '快乐暑期', '皮肤科'),
('MED5', 'H5', '腋下止汗祛味（国产） +2000可升级进口产品', 1599.00, '快乐暑期', '皮肤科'),
('MED6', 'H6', '夏日修复紧致套餐：黄金点阵射频全面部单次 + 下颌缘 + 医用修复面膜', 4420.00, '快乐暑期', '皮肤科'),
('MED7', 'H7', '夏日补水美白套餐：黑金超光子DPL/BBL + 氧活泡泡针2.5 ml', 1699.00, '快乐暑期', '皮肤科'),
('MED8', 'H8', '夏日亮肤套餐：化学焕肤全面部（果酸/水杨酸） + 黑金超光子DPL/BBL + 小气泡清洁', 2199.00, '快乐暑期', '皮肤科'),
-- Dental services
('MED9', 'H1', '"健康小先锋"成长套餐（四选二）', 188.00, '儿童骨龄检测、深度视力筛查、儿童全口涂氟、OK镜验配（任选二）', '儿童牙科/口腔科'),
('MED10', 'H2', '皓得适牙齿诊间美白3次卡', 2880.00, '美白3次次卡', '口腔科'),
('MED11', 'H3', '芬兰罗慕咬合诱导儿童牙矫治', 23800.00, '夜间佩戴、早期矫正、咬合诱导技术', '儿童牙科/口腔科'),
('MED12', 'H4', '牙齿矫正/种植咨询（含拍片）', 199.00, '专业口腔检查 + 矫正/种植医生面诊', '口腔科'),
('MED13', 'H5', '矫正/种植/贴面检查及方案咨询', 29.90, '一站式口腔健康管理', '口腔科'),
('MED14', 'H6', 'iTero口扫正畸评估方案', 199.00, '数字化口扫评估', '口腔科'),
('MED15', 'H7', '韩国奥齿泰种植牙系统（指定型号）', 4999.00, '指定型号 + 赠送锆瓷牙冠', '口腔科'),
('MED16', 'H8', '儿童窝沟封闭（限首颗）', 118.00, '填补窝沟、预防龋齿', '儿童牙科/口腔科'),
-- Eye care services
('MED17', 'H1', '儿童远视储备管理2年卡', 1980.00, '原明眸睛彩计划', '眼科'),
('MED18', 'H2', '成人配镜（特殊镜片有效避免视疲劳）', 3178.00, '特殊镜片设计', '眼科'),
('MED19', 'H3', '成人配镜检查套餐（医疗级）', 699.00, '专业配镜检查、个性化方案、赠镜架+镜片', '眼科'),
('MED20', 'H4', '儿童视力及足脊筛查套餐', 468.00, '视力检查、扁平足筛查、脊柱侧弯筛查', '眼科'),
('MED21', 'H5', '青少年近视管理配镜套餐', 3580.00, '科学验光、价值3980组合趣味镜片、3对1眼健康服务', '眼科'),
('MED22', 'H6', '角膜塑形镜（OK镜）验配套餐', 12800.00, '专业近视防控', '眼科'),
('MED23', 'H7', '青少年近视防控神器-拉远镜', 2680.00, '物理拉远训练', '眼科'),
-- Child growth and rehabilitation services
('MED24', 'H1', '儿童身高潜力评估（骨龄 + 医生解读报告）', 199.00, '身高预测 + 个性化生长方案', '儿童成长科'),
('MED25', 'H2', '女性康复评估（首次）', 29.90, '女性专项康复评估', '运动康复科'),
('MED26', 'H3', '肋骨外翻矫正治疗单次卡（含评估）', 218.00, '肋骨外翻评估 + 治疗', '运动康复科'),
('MED27', 'H4', '跑步膝/跳跃膝损伤防护治疗单次卡（含评估）', 218.00, '运动损伤评估 + 防护治疗', '运动康复科');

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_schedules_doctor_date ON humansa_schedule(doctor_code, shift_date);
CREATE INDEX IF NOT EXISTS idx_schedules_clinic_date ON humansa_schedule(clinic_code, shift_date);
CREATE INDEX IF NOT EXISTS idx_schedules_date ON humansa_schedule(shift_date);
CREATE INDEX IF NOT EXISTS idx_doctors_name ON humansa_doctor(name);
CREATE INDEX IF NOT EXISTS idx_clinics_city ON humansa_clinics(city);
CREATE INDEX IF NOT EXISTS idx_services_name ON humansa_service(name);
CREATE INDEX IF NOT EXISTS idx_medical_services_name ON humansa_medical_service(name);

-- Product tables (matches humansa_products)
CREATE TABLE IF NOT EXISTS humansa_product_category (
    category_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_category_id VARCHAR(20) REFERENCES humansa_product_category(category_id)
);

CREATE TABLE IF NOT EXISTS humansa_products (
    product_id VARCHAR(30) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category_id VARCHAR(20) REFERENCES humansa_product_category(category_id),
    price DECIMAL(10,2),
    original_price DECIMAL(10,2),
    discount_tag VARCHAR(50),
    description TEXT,
    benefits TEXT,
    usage_instructions TEXT,
    suitable_for TEXT,
    stock_status VARCHAR(20) DEFAULT 'in_stock',
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS humansa_product_packages (
    package_id VARCHAR(30) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10,2),
    original_price DECIMAL(10,2),
    discount_percentage INTEGER,
    description TEXT,
    includes TEXT,
    valid_days INTEGER,
    purchase_limit INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert product categories
INSERT INTO humansa_product_category (category_id, name, description) VALUES
('CAT1', '营养保健', '维生素、矿物质、保健品'),
('CAT2', '医疗器械', '家用医疗设备和监测器材'),
('CAT3', '护肤美容', '医美级护肤品'),
('CAT4', '中医养生', '中药材、养生茶饮'),
('CAT5', '母婴健康', '孕妇及婴幼儿专用产品');

-- Insert products
INSERT INTO humansa_products (product_id, name, category_id, price, original_price, discount_tag, description, benefits, suitable_for) VALUES
-- 营养保健类
('PROD001', '诺亚新舟维生素D3软胶囊', 'CAT1', 168.00, 198.00, '限时特惠', '高纯度维生素D3，每粒含2000IU', '增强免疫力，促进钙吸收，改善骨骼健康', '成人及老年人'),
('PROD002', '深海鱼油Omega-3胶囊', 'CAT1', 298.00, 398.00, '会员专享', '挪威进口深海鱼油，DHA+EPA黄金配比', '保护心血管，改善记忆力，抗炎抗氧化', '中老年人群'),
('PROD003', '益生菌冻干粉', 'CAT1', 238.00, 288.00, '新品上市', '10种活性益生菌，100亿CFU/袋', '调节肠道菌群，提高免疫力，改善消化', '全年龄段'),
('PROD004', '胶原蛋白肽饮品', 'CAT1', 468.00, 568.00, '美容养颜', '小分子胶原蛋白肽，添加维C和透明质酸', '改善皮肤弹性，减少皱纹，美白保湿', '25岁以上女性'),
('PROD005', '综合维生素片', 'CAT1', 158.00, NULL, NULL, '23种维生素矿物质，科学配比', '补充日常营养，提高身体机能', '成年人'),
('PROD006', '辅酶Q10软胶囊', 'CAT1', 328.00, 428.00, '心脏守护', '每粒含辅酶Q10 100mg', '保护心脏，抗氧化，提高能量代谢', '40岁以上人群'),

-- 医疗器械类
('PROD007', '智能血压计', 'CAT2', 399.00, 499.00, '爆款热卖', '全自动臂式，APP连接，语音播报', '精准测量，历史记录，异常提醒', '高血压患者及家庭'),
('PROD008', '血糖仪套装', 'CAT2', 268.00, 368.00, '糖友必备', '含血糖仪+100试纸+采血针', '快速准确，微量采血，数据存储', '糖尿病患者'),
('PROD009', '便携式制氧机', 'CAT2', 2880.00, 3680.00, '呼吸守护', '5L医用级，低噪音，可调节浓度', '改善缺氧，辅助呼吸，提高血氧', '老年人及呼吸疾病患者'),
('PROD010', '红外额温枪', 'CAT2', 158.00, 198.00, '防疫必备', '非接触测温，1秒出结果，记忆功能', '快速筛查，安全卫生，精准度高', '家庭及公共场所'),
('PROD011', '智能体脂秤', 'CAT2', 298.00, NULL, NULL, '测量13项身体数据，APP管理', '全面了解身体状况，制定健康计划', '健身及体重管理人群'),

-- 护肤美容类
('PROD012', '医美修复面膜', 'CAT3', 368.00, 468.00, '术后修复', '医用级无菌包装，透明质酸+胶原蛋白', '修复受损肌肤，补水保湿，舒缓镇静', '医美术后及敏感肌'),
('PROD013', '美白淡斑精华', 'CAT3', 588.00, 788.00, '明星产品', '烟酰胺+维C衍生物，淡化色斑', '美白提亮，淡化斑点，均匀肤色', '有色斑困扰人群'),
('PROD014', '抗衰老面霜', 'CAT3', 698.00, 898.00, '贵妇首选', '视黄醇+多肽复合物，深层抗皱', '减少皱纹，提升紧致，延缓衰老', '35岁以上人群'),
('PROD015', '舒敏保湿乳', 'CAT3', 268.00, NULL, NULL, '神经酰胺+角鲨烷，修复屏障', '深层保湿，修复敏感，增强屏障', '敏感肌及干性肌肤'),

-- 中医养生类
('PROD016', '西洋参含片', 'CAT4', 298.00, 398.00, '养生佳品', '加拿大进口西洋参，独立包装', '补气养阴，清热生津，提高免疫力', '体虚易疲劳人群'),
('PROD017', '灵芝孢子粉', 'CAT4', 568.00, 768.00, '破壁技术', '破壁灵芝孢子粉，吸收率高', '增强免疫，保肝护肝，改善睡眠', '免疫力低下人群'),
('PROD018', '枸杞原浆', 'CAT4', 228.00, 288.00, '宁夏特产', '100%纯枸杞鲜榨，无添加', '明目护肝，补肾益精，抗氧化', '用眼过度及肾虚人群'),
('PROD019', '燕窝即食', 'CAT4', 888.00, 1288.00, '滋补圣品', '印尼进口燕窝，即开即食', '美容养颜，润肺止咳，提高免疫', '女性及呼吸道疾病患者'),
('PROD020', '三七粉', 'CAT4', 368.00, NULL, NULL, '云南文山三七，超细粉', '活血化瘀，消肿止痛，保护心脑血管', '心脑血管疾病高危人群'),

-- 母婴健康类
('PROD021', '孕妇DHA藻油', 'CAT5', 398.00, 498.00, '孕期必备', '植物来源DHA，每粒200mg', '促进胎儿大脑发育，改善记忆力', '孕期及哺乳期妇女'),
('PROD022', '婴幼儿益生菌', 'CAT5', 268.00, 328.00, '宝宝肠道卫士', '专为0-3岁设计，添加益生元', '改善腹泻便秘，提高免疫力', '0-3岁婴幼儿'),
('PROD023', '孕妇钙片', 'CAT5', 168.00, NULL, NULL, '钙+维生素D3，柠檬酸钙易吸收', '预防骨质疏松，促进胎儿骨骼发育', '孕期及哺乳期妇女'),
('PROD024', '婴儿维生素D滴剂', 'CAT5', 128.00, 158.00, '儿科推荐', '每滴400IU，无色无味', '预防佝偻病，促进钙吸收', '0-2岁婴幼儿'),
('PROD025', '产后修复套装', 'CAT5', 1288.00, 1688.00, '月子必备', '含收腹带+盆底肌修复仪+护理垫', '帮助产后恢复，预防脱垂', '产后妈妈');

-- Insert product packages
INSERT INTO humansa_product_packages (package_id, name, category, price, original_price, discount_percentage, description, includes, valid_days) VALUES
('PKG101', '三高管理套餐', '慢病管理', 1588.00, 2088.00, 24, '针对高血压、高血糖、高血脂人群的综合管理方案', '血压计+血糖仪+血脂四项检测+营养指导+3个月随访', 90),
('PKG102', '孕期营养套餐', '母婴健康', 1888.00, 2588.00, 27, '覆盖整个孕期的营养补充方案', 'DHA+钙片+综合维生素+叶酸+铁剂+营养师咨询', 280),
('PKG103', '抗衰老美容套餐', '护肤美容', 2888.00, 3888.00, 26, '医美级抗衰老护肤方案', '抗衰面霜+精华+面膜10片+美容仪+皮肤检测', 180),
('PKG104', '免疫力提升套餐', '营养保健', 1288.00, 1688.00, 24, '全面提升免疫力的营养方案', '维生素C+维生素D+益生菌+灵芝孢子粉+健康评估', 60),
('PKG105', '企业员工健康包', '健康管理', 688.00, 888.00, 23, '企业团购专享健康礼包', '体检券+维生素+口罩+消毒液+健康讲座', 365),
('PKG106', '老年人关爱套餐', '老年健康', 1988.00, 2688.00, 26, '专为65岁以上老年人设计', '血压计+制氧机试用+钙片+关节保健品+上门体检', 120),
('PKG107', '运动营养套餐', '运动健身', 988.00, 1388.00, 29, '运动爱好者专属营养方案', '蛋白粉+BCAA+维生素+电解质饮料+运动损伤咨询', 90),
('PKG108', '睡眠改善套餐', '睡眠健康', 1388.00, 1888.00, 26, '改善睡眠质量的综合方案', '褪黑素+助眠枕+香薰+睡眠监测手环+专家咨询', 60);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_products_category ON humansa_products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_name ON humansa_products(name);
CREATE INDEX IF NOT EXISTS idx_products_featured ON humansa_products(is_featured);
CREATE INDEX IF NOT EXISTS idx_packages_category ON humansa_product_packages(category);

-- Grant permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;