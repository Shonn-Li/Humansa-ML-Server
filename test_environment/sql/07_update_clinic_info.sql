-- Update clinic information with complete details
-- This script adds missing information to clinic records

-- First, add columns if they don't exist
ALTER TABLE humansa_clinics ADD COLUMN IF NOT EXISTS region VARCHAR(100);
ALTER TABLE humansa_clinics ADD COLUMN IF NOT EXISTS type VARCHAR(50) DEFAULT 'comprehensive';
ALTER TABLE humansa_clinics ADD COLUMN IF NOT EXISTS email VARCHAR(100);
ALTER TABLE humansa_clinics ADD COLUMN IF NOT EXISTS operating_hours JSONB;
ALTER TABLE humansa_clinics ADD COLUMN IF NOT EXISTS facilities TEXT[];
ALTER TABLE humansa_clinics ADD COLUMN IF NOT EXISTS parking BOOLEAN DEFAULT true;
ALTER TABLE humansa_clinics ADD COLUMN IF NOT EXISTS wheelchair_accessible BOOLEAN DEFAULT true;
ALTER TABLE humansa_clinics ADD COLUMN IF NOT EXISTS nearest_mrt VARCHAR(200);
ALTER TABLE humansa_clinics ADD COLUMN IF NOT EXISTS languages TEXT[] DEFAULT ARRAY['中文', 'English'];

-- Update existing clinic records with complete information
UPDATE humansa_clinics SET
    region = city,
    type = 'comprehensive',
    email = LOWER(clinic_code) || '@humansa.com',
    operating_hours = '{
        "monday": "08:00-20:00",
        "tuesday": "08:00-20:00",
        "wednesday": "08:00-20:00",
        "thursday": "08:00-20:00",
        "friday": "08:00-20:00",
        "saturday": "09:00-18:00",
        "sunday": "09:00-18:00"
    }'::jsonb,
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound'],
    parking = true,
    wheelchair_accessible = true,
    languages = ARRAY['中文', 'English', '粤语']
WHERE clinic_code IN ('H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H8', 'H9', 'H10', 'H11', 'H12', 'H13', 'H14', 'H15');

-- Update specific clinic details
UPDATE humansa_clinics SET
    nearest_mrt = '国贸站 (地铁1号线/10号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', 'CT', 'MRI']
WHERE clinic_code = 'H1';

UPDATE humansa_clinics SET
    nearest_mrt = '陆家嘴站 (地铁2号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', 'CT', 'MRI', '内窥镜中心']
WHERE clinic_code = 'H2';

UPDATE humansa_clinics SET
    nearest_mrt = '珠江新城站 (地铁3号线/5号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', 'CT', '体检中心']
WHERE clinic_code = 'H3';

UPDATE humansa_clinics SET
    nearest_mrt = '会展中心站 (地铁1号线/4号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', 'CT', 'MRI', '日间手术中心']
WHERE clinic_code = 'H4';

UPDATE humansa_clinics SET
    nearest_mrt = '龙翔桥站 (地铁1号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', '中医理疗']
WHERE clinic_code = 'H5';

UPDATE humansa_clinics SET
    nearest_mrt = '元通站 (地铁2号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', '康复中心']
WHERE clinic_code = 'H6';

UPDATE humansa_clinics SET
    nearest_mrt = '小白楼站 (地铁1号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', '心理咨询']
WHERE clinic_code = 'H7';

UPDATE humansa_clinics SET
    nearest_mrt = '时代广场站 (地铁1号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', '齿科中心']
WHERE clinic_code = 'H8';

UPDATE humansa_clinics SET
    nearest_mrt = '春熙路站 (地铁2号线/3号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', '皮肤美容']
WHERE clinic_code = 'H9';

UPDATE humansa_clinics SET
    nearest_mrt = '较场口站 (轻轨1号线/2号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', '眼科中心']
WHERE clinic_code = 'H10';

UPDATE humansa_clinics SET
    nearest_mrt = '中南路站 (地铁2号线/4号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', '妇产中心']
WHERE clinic_code = 'H11';

UPDATE humansa_clinics SET
    nearest_mrt = '高新技术开发区站 (地铁3号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', '运动医学']
WHERE clinic_code = 'H12';

UPDATE humansa_clinics SET
    nearest_mrt = '五一广场站 (地铁1号线/2号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', '营养科']
WHERE clinic_code = 'H13';

UPDATE humansa_clinics SET
    nearest_mrt = '五四广场站 (地铁3号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', '睡眠中心']
WHERE clinic_code = 'H14';

UPDATE humansa_clinics SET
    nearest_mrt = '天一广场站 (地铁1号线)',
    facilities = ARRAY['WiFi', 'Parking', 'Pharmacy', 'Laboratory', 'X-Ray', 'Ultrasound', '过敏中心']
WHERE clinic_code = 'H15';

-- Add special operating hours for some clinics
UPDATE humansa_clinics SET
    operating_hours = '{
        "monday": "07:30-21:00",
        "tuesday": "07:30-21:00",
        "wednesday": "07:30-21:00",
        "thursday": "07:30-21:00",
        "friday": "07:30-21:00",
        "saturday": "08:00-20:00",
        "sunday": "08:00-20:00"
    }'::jsonb
WHERE clinic_code IN ('H1', 'H2', 'H3', 'H4'); -- Major cities have extended hours

-- Verify the updates
SELECT clinic_code, name, city, nearest_mrt, 
       array_length(facilities, 1) as facility_count,
       operating_hours->>'monday' as monday_hours
FROM humansa_clinics
ORDER BY clinic_code;