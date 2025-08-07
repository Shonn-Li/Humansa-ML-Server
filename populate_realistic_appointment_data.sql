-- Populate realistic appointment slots and bookings for testing
-- Creates appointment slots from current date to next 2 weeks
-- Ensures realistic booking patterns and availability

BEGIN;

-- Clear existing data
TRUNCATE TABLE humansa_appointment_slots CASCADE;
TRUNCATE TABLE humansa_appointments CASCADE;

-- Set registration fees for doctors if missing
UPDATE humansa_doctor 
SET registration_fee = CASE 
    WHEN specialty LIKE '%专家%' OR specialty LIKE '%主任%' THEN 200
    WHEN specialty LIKE '%副主任%' THEN 150
    WHEN specialty IN ('心内科', '神经外科', '骨科') THEN 120
    ELSE 80
END
WHERE registration_fee IS NULL;

-- Generate appointment slots for next 14 days (2 weeks)
INSERT INTO humansa_appointment_slots (doctor_id, clinic_id, date, time, consultation_type, consultation_fee, is_available)
SELECT 
    d.doctor_code as doctor_id,
    d.clinic_code as clinic_id,
    date_series.slot_date,
    time_series.slot_time,
    CASE 
        WHEN random() < 0.2 THEN 'online'  -- 20% online consultations
        ELSE 'in-person'
    END as consultation_type,
    COALESCE(d.registration_fee, 80) as consultation_fee,
    CASE 
        -- Monday-Friday: Higher availability (80%)
        WHEN EXTRACT(DOW FROM date_series.slot_date) BETWEEN 1 AND 5 THEN
            CASE WHEN random() < 0.8 THEN true ELSE false END
        -- Saturday: Moderate availability (60%)  
        WHEN EXTRACT(DOW FROM date_series.slot_date) = 6 THEN
            CASE WHEN random() < 0.6 THEN true ELSE false END
        -- Sunday: Lower availability (30%)
        ELSE 
            CASE WHEN random() < 0.3 THEN true ELSE false END
    END as is_available
FROM 
    humansa_doctor d
CROSS JOIN 
    -- Generate dates for next 14 days (including today)
    generate_series(
        CURRENT_DATE,
        CURRENT_DATE + INTERVAL '13 days',
        '1 day'::interval
    ) as date_series(slot_date)
CROSS JOIN
    -- Generate realistic time slots
    (VALUES 
        -- Morning slots (9 AM - 12 PM)
        ('09:00'::time), ('09:30'::time), ('10:00'::time), ('10:30'::time), 
        ('11:00'::time), ('11:30'::time),
        -- Afternoon slots (2 PM - 6 PM) 
        ('14:00'::time), ('14:30'::time), ('15:00'::time), ('15:30'::time), 
        ('16:00'::time), ('16:30'::time), ('17:00'::time), ('17:30'::time)
    ) as time_series(slot_time)
WHERE 
    -- Skip past time slots for today
    (date_series.slot_date > CURRENT_DATE OR 
     (date_series.slot_date = CURRENT_DATE AND time_series.slot_time > CURRENT_TIME))
    -- Each doctor has some slots but not all
    AND random() < 0.7;  -- 70% chance for each doctor-time combination

-- Ensure guaranteed availability for key specialties in next 3 days
-- Heart specialist (心内科) - Dr. 孙浩 (DOC007)
UPDATE humansa_appointment_slots 
SET is_available = true 
WHERE doctor_id = 'DOC007' 
AND date BETWEEN CURRENT_DATE AND CURRENT_DATE + 3
AND time IN ('09:00', '10:00', '14:00', '15:00');

-- Pediatrics (儿科) - Dr. 李娜 (DOC002)  
UPDATE humansa_appointment_slots 
SET is_available = true 
WHERE doctor_id = 'DOC002' 
AND date BETWEEN CURRENT_DATE AND CURRENT_DATE + 3
AND time IN ('09:30', '10:30', '14:30', '15:30');

-- Internal Medicine (内科) - Dr. 王强 (DOC003)
UPDATE humansa_appointment_slots 
SET is_available = true 
WHERE doctor_id = 'DOC003' 
AND date BETWEEN CURRENT_DATE AND CURRENT_DATE + 3
AND time IN ('10:00', '11:00', '15:00', '16:00');

-- Traditional Chinese Medicine (中医科) - Dr. 郑雪 (DOC010)
UPDATE humansa_appointment_slots 
SET is_available = true 
WHERE doctor_id = 'DOC010' 
AND date BETWEEN CURRENT_DATE AND CURRENT_DATE + 3
AND time IN ('09:00', '11:00', '14:00', '16:00');

-- Dermatology (皮肤科) - Dr. 赵丽 (DOC006)
UPDATE humansa_appointment_slots 
SET is_available = true 
WHERE doctor_id = 'DOC006' 
AND date BETWEEN CURRENT_DATE AND CURRENT_DATE + 3
AND time IN ('10:30', '11:30', '15:30', '16:30');

-- Create realistic booked appointments using existing appointments table structure
-- Insert appointments for unavailable slots
INSERT INTO humansa_appointments (schedule_id, patient_name, patient_phone, appointment_time, status, created_at)
SELECT 
    s.slot_id as schedule_id,
    CASE (random() * 10)::int
        WHEN 0 THEN '张小明'
        WHEN 1 THEN '李小红'
        WHEN 2 THEN '王小强' 
        WHEN 3 THEN '刘小芳'
        WHEN 4 THEN '陈小华'
        WHEN 5 THEN '赵小丽'
        WHEN 6 THEN '孙小浩'
        WHEN 7 THEN '周小敏'
        WHEN 8 THEN '吴小刚'
        ELSE '郑小雪'
    END as patient_name,
    '138' || LPAD(floor(random() * 100000000)::text, 8, '0') as patient_phone,
    s.time,
    CASE 
        WHEN s.date > CURRENT_DATE THEN 'confirmed'
        WHEN s.date = CURRENT_DATE AND s.time > CURRENT_TIME THEN 'confirmed'
        ELSE 'completed'
    END as status,
    CURRENT_TIMESTAMP - INTERVAL '1 hour' * floor(random() * 168) as created_at -- Random time in past week
FROM humansa_appointment_slots s
WHERE s.is_available = false
    AND random() < 0.8  -- 80% of unavailable slots have appointments
LIMIT 100;  -- Cap at 100 appointments for testing

-- Mark slots as unavailable where appointments exist
UPDATE humansa_appointment_slots 
SET is_available = false
WHERE slot_id IN (
    SELECT DISTINCT schedule_id 
    FROM humansa_appointments 
    WHERE schedule_id IS NOT NULL
);

-- Create temp table for summary statistics
CREATE TEMP TABLE temp_summary (category text, subcategory text, count int);

-- Total slots created
INSERT INTO temp_summary VALUES ('Total Slots Created', '', (SELECT COUNT(*) FROM humansa_appointment_slots));

-- Available slots by date

INSERT INTO temp_summary
SELECT 
    'Available Slots by Date' as category,
    slot_date::text as subcategory,
    COUNT(*) as count
FROM (
    SELECT date as slot_date
    FROM humansa_appointment_slots 
    WHERE is_available = true 
    AND date BETWEEN CURRENT_DATE AND CURRENT_DATE + 6
) subq
GROUP BY slot_date
ORDER BY slot_date;

-- Available slots by specialty
INSERT INTO temp_summary
SELECT 
    'Available Slots by Specialty' as category,
    d.specialty as subcategory,
    COUNT(*) as count
FROM humansa_appointment_slots s
JOIN humansa_doctor d ON s.doctor_id = d.doctor_code
WHERE s.is_available = true 
AND s.date BETWEEN CURRENT_DATE AND CURRENT_DATE + 6
GROUP BY d.specialty
ORDER BY count DESC;

-- Show summary
SELECT 
    category,
    CASE WHEN subcategory = '' THEN 'Total' ELSE subcategory END as detail,
    count
FROM temp_summary
ORDER BY 
    CASE category 
        WHEN 'Summary Statistics' THEN 1
        WHEN 'Available Slots by Date' THEN 2  
        WHEN 'Available Slots by Specialty' THEN 3
    END,
    subcategory;

DROP TABLE temp_summary;

-- Show some sample available appointments for testing
SELECT 
    d.name as doctor_name,
    d.specialty,
    s.date,
    s.time,
    s.consultation_type,
    s.consultation_fee,
    c.name as clinic_name
FROM humansa_appointment_slots s
JOIN humansa_doctor d ON s.doctor_id = d.doctor_code
LEFT JOIN humansa_clinics c ON s.clinic_id = c.clinic_code
WHERE s.is_available = true 
AND s.date BETWEEN CURRENT_DATE AND CURRENT_DATE + 2
ORDER BY s.date, s.time, d.specialty
LIMIT 20;

COMMIT;