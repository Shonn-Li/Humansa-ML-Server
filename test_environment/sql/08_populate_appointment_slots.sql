-- Populate appointment_slots table with test data
-- This creates available appointment slots for the next 30 days

-- First create the table if it doesn't exist
CREATE TABLE IF NOT EXISTS humansa_appointment_slots (
    slot_id SERIAL PRIMARY KEY,
    doctor_id VARCHAR(20) REFERENCES humansa_doctor(doctor_code),
    clinic_id VARCHAR(20) REFERENCES humansa_clinics(clinic_code),
    date DATE NOT NULL,
    time TIME NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    consultation_type VARCHAR(50) DEFAULT 'in-person',
    consultation_fee DECIMAL(10,2),
    is_available BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_appointment_slots_doctor_date ON humansa_appointment_slots(doctor_id, date);
CREATE INDEX IF NOT EXISTS idx_appointment_slots_available ON humansa_appointment_slots(is_available, date);

-- Clear existing slots
TRUNCATE TABLE humansa_appointment_slots CASCADE;

-- Generate appointment slots for each doctor for the next 30 days
INSERT INTO humansa_appointment_slots (doctor_id, clinic_id, date, time, consultation_type, consultation_fee, is_available)
SELECT 
    d.doctor_code as doctor_id,
    d.clinic_code as clinic_id,
    date_series.slot_date,
    time_series.slot_time,
    CASE 
        WHEN random() < 0.3 THEN 'online'
        ELSE 'in-person'
    END as consultation_type,
    d.registration_fee,
    CASE 
        WHEN random() < 0.7 THEN true  -- 70% of slots are available
        ELSE false
    END as is_available
FROM 
    humansa_doctor d
CROSS JOIN 
    -- Generate dates for next 30 days
    generate_series(
        CURRENT_DATE + INTERVAL '1 day',
        CURRENT_DATE + INTERVAL '30 days',
        '1 day'::interval
    ) as date_series(slot_date)
CROSS JOIN
    -- Generate time slots (morning and afternoon sessions)
    (VALUES 
        ('09:00'::time), ('09:30'::time), ('10:00'::time), ('10:30'::time), ('11:00'::time), ('11:30'::time),
        ('14:00'::time), ('14:30'::time), ('15:00'::time), ('15:30'::time), ('16:00'::time), ('16:30'::time), ('17:00'::time)
    ) as time_series(slot_time)
WHERE 
    -- Skip weekends for some doctors
    (EXTRACT(DOW FROM date_series.slot_date) NOT IN (0, 6) OR d.doctor_code IN ('D1', 'D2', 'D3', 'D4', 'D5'))
    -- Limit slots per doctor per day
    AND random() < 0.6;

-- Ensure some specific slots are available for testing
-- Doctor 张三 (D1) - ensure slots for next few days
UPDATE humansa_appointment_slots 
SET is_available = true 
WHERE doctor_id = 'D1' 
AND date BETWEEN CURRENT_DATE + 1 AND CURRENT_DATE + 7
AND time IN ('09:00', '10:00', '14:00', '15:00');

-- Doctor 李四 (D2) - ensure slots for next few days
UPDATE humansa_appointment_slots 
SET is_available = true 
WHERE doctor_id = 'D2' 
AND date BETWEEN CURRENT_DATE + 1 AND CURRENT_DATE + 7
AND time IN ('09:30', '10:30', '14:30', '15:30');

-- Doctor 王五 (D3) - ensure slots for next few days
UPDATE humansa_appointment_slots 
SET is_available = true 
WHERE doctor_id = 'D3' 
AND date BETWEEN CURRENT_DATE + 1 AND CURRENT_DATE + 7
AND time IN ('10:00', '11:00', '15:00', '16:00');

-- Create some booked appointments for testing
INSERT INTO humansa_appointments (appointment_id, slot_id, user_id, doctor_id, clinic_id, appointment_date, appointment_time, consultation_type, status, reason_for_visit, consultation_fee, created_at, confirmed_at)
SELECT 
    'test_apt_' || s.slot_id,
    s.slot_id,
    'test_user_' || (floor(random() * 100 + 1))::text,
    s.doctor_id,
    s.clinic_id,
    s.date,
    s.time,
    s.consultation_type,
    'scheduled',
    CASE floor(random() * 5)
        WHEN 0 THEN '常规体检'
        WHEN 1 THEN '感冒发烧'
        WHEN 2 THEN '慢病复诊'
        WHEN 3 THEN '健康咨询'
        ELSE '专科检查'
    END,
    s.consultation_fee,
    NOW() - INTERVAL '1 day' * floor(random() * 7),
    NOW() - INTERVAL '1 day' * floor(random() * 7)
FROM humansa_appointment_slots s
WHERE s.is_available = false
LIMIT 50;

-- Verify the data
SELECT 
    'Total slots created' as metric,
    COUNT(*) as count
FROM humansa_appointment_slots
UNION ALL
SELECT 
    'Available slots' as metric,
    COUNT(*) as count
FROM humansa_appointment_slots
WHERE is_available = true
UNION ALL
SELECT 
    'Booked appointments' as metric,
    COUNT(*) as count
FROM humansa_appointments
WHERE status = 'scheduled';

-- Show sample availability for first 3 doctors
SELECT 
    d.name as doctor_name,
    s.date,
    COUNT(*) FILTER (WHERE s.is_available = true) as available_slots,
    COUNT(*) as total_slots
FROM humansa_appointment_slots s
JOIN humansa_doctor d ON s.doctor_id = d.doctor_code
WHERE s.date BETWEEN CURRENT_DATE + 1 AND CURRENT_DATE + 7
AND d.doctor_code IN ('D1', 'D2', 'D3')
GROUP BY d.name, s.date
ORDER BY d.name, s.date;