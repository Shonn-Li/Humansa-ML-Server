-- Create Humansa tables for testing

-- Create clinics table
CREATE TABLE IF NOT EXISTS humansa_clinics (
    id SERIAL PRIMARY KEY,
    clinic_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    address TEXT,
    phone VARCHAR(50),
    operating_hours VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create doctors table
CREATE TABLE IF NOT EXISTS humansa_doctor (
    id SERIAL PRIMARY KEY,
    doctor_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    specialty VARCHAR(100),
    clinic_code VARCHAR(50) REFERENCES humansa_clinics(clinic_code),
    city VARCHAR(100),
    language VARCHAR(50) DEFAULT 'zh',
    phone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create schedule table
CREATE TABLE IF NOT EXISTS humansa_schedule (
    id SERIAL PRIMARY KEY,
    doctor_code VARCHAR(50) REFERENCES humansa_doctor(doctor_code),
    clinic_code VARCHAR(50) REFERENCES humansa_clinics(clinic_code),
    date DATE NOT NULL,
    time_slot VARCHAR(50),
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create medical service table
CREATE TABLE IF NOT EXISTS humansa_medical_service (
    id SERIAL PRIMARY KEY,
    service_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10,2),
    currency VARCHAR(10) DEFAULT 'CNY',
    clinic_code VARCHAR(50) REFERENCES humansa_clinics(clinic_code),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert test data
INSERT INTO humansa_clinics (clinic_code, name, city, address, phone, operating_hours) VALUES
('CL001', '北京协和医院', '北京', '北京市东城区帅府园1号', '010-69156114', '周一至周五 8:00-17:00'),
('CL002', '深圳人民医院', '深圳', '深圳市罗湖区东门北路1017号', '0755-25533018', '周一至周六 8:00-18:00'),
('CL003', '广州中山医院', '广州', '广州市越秀区中山二路106号', '020-87755766', '周一至周日 8:00-20:00')
ON CONFLICT (clinic_code) DO NOTHING;

INSERT INTO humansa_doctor (doctor_code, name, specialty, clinic_code, city, language) VALUES
('DR001', '王医生', '心内科', 'CL001', '北京', 'zh'),
('DR002', '李医生', '骨科', 'CL001', '北京', 'zh'),
('DR003', '张医生', '心脏科', 'CL002', '深圳', 'zh'),
('DR004', '刘医生', '神经内科', 'CL003', '广州', 'zh')
ON CONFLICT (doctor_code) DO NOTHING;

-- Add some schedule data for next week
INSERT INTO humansa_schedule (doctor_code, clinic_code, date, time_slot, is_available) VALUES
('DR001', 'CL001', CURRENT_DATE + INTERVAL '1 day', '09:00', true),
('DR001', 'CL001', CURRENT_DATE + INTERVAL '1 day', '10:00', true),
('DR001', 'CL001', CURRENT_DATE + INTERVAL '2 days', '14:00', true),
('DR002', 'CL001', CURRENT_DATE + INTERVAL '1 day', '11:00', true),
('DR003', 'CL002', CURRENT_DATE + INTERVAL '3 days', '15:00', true)
ON CONFLICT DO NOTHING;

INSERT INTO humansa_medical_service (service_code, name, category, price, clinic_code) VALUES
('SV001', '肝功能检查', '检验科', 280.00, 'CL001'),
('SV002', '核磁共振', '影像科', 1200.00, 'CL001'),
('SV003', '体检套餐A', '体检', 580.00, 'CL002'),
('SV004', '体检套餐B', '体检', 980.00, 'CL003')
ON CONFLICT (service_code) DO NOTHING;