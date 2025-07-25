#!/bin/bash
# Apply Humansa improvements to existing database

echo "🚀 Applying Humansa Agent Improvements..."

# Apply database changes
echo "📊 Updating database with missing tables..."
psql -h localhost -p 5432 -U postgres -d test4 << 'EOF'
-- Create missing Humansa tables if they don't exist
CREATE TABLE IF NOT EXISTS humansa_clinic (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    phone VARCHAR(50),
    email VARCHAR(255),
    operating_hours TEXT,
    services TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS humansa_medical_service (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    duration_minutes INTEGER,
    price_range_min DECIMAL(10,2),
    price_range_max DECIMAL(10,2),
    available_at_clinics INTEGER[],
    requires_appointment BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert seed data
INSERT INTO humansa_clinic (name, address, phone, email, operating_hours, services) VALUES
('Humansa Clinic Kowloon', '123 Nathan Road, Tsim Sha Tsui, Kowloon', '+852 2345 6789', 'kowloon@humansa.com', 'Mon-Fri: 9:00-18:00, Sat: 9:00-13:00', ARRAY['General Practice', 'Specialist Consultation', 'Health Screening']),
('Humansa Clinic Central', '456 Queens Road Central, Central, Hong Kong Island', '+852 2789 0123', 'central@humansa.com', 'Mon-Fri: 8:30-19:00, Sat: 9:00-14:00', ARRAY['General Practice', 'Dermatology', 'Cardiology']),
('Humansa Clinic Causeway Bay', '789 Hennessy Road, Causeway Bay, Hong Kong Island', '+852 2567 8901', 'causewaybay@humansa.com', 'Mon-Sat: 9:00-20:00, Sun: 10:00-16:00', ARRAY['General Practice', 'Pediatrics', 'Vaccination'])
ON CONFLICT DO NOTHING;

INSERT INTO humansa_medical_service (service_name, category, description, duration_minutes, price_range_min, price_range_max, available_at_clinics, requires_appointment) VALUES
('General Consultation', 'General Practice', 'General medical consultation for common illnesses', 30, 300.00, 500.00, ARRAY[1,2,3], TRUE),
('Health Screening Basic', 'Preventive Care', 'Basic health screening including blood tests', 60, 800.00, 1200.00, ARRAY[1,2,3], TRUE),
('Dermatology Consultation', 'Specialist', 'Specialist consultation for skin conditions', 45, 800.00, 1500.00, ARRAY[2], TRUE),
('Cardiology Consultation', 'Specialist', 'Heart specialist consultation with ECG', 60, 1200.00, 2000.00, ARRAY[2], TRUE),
('Pediatric Consultation', 'Specialist', 'Children health consultation', 45, 500.00, 800.00, ARRAY[3], TRUE)
ON CONFLICT DO NOTHING;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Database updated successfully"
else
    echo "❌ Failed to update database"
    exit 1
fi

echo ""
echo "✅ Humansa improvements applied!"
echo ""
echo "Next steps:"
echo "1. Run the test environment: ./run_humansa_test_environment.sh"
echo "2. The test script will automatically apply agent enhancements"
echo "3. Check test results for ≥90% pass rate"