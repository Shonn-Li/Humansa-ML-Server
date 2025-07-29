-- Fix medical service table schema to match insert statements
-- Drop and recreate the table with correct columns

-- Drop existing table if it exists
DROP TABLE IF EXISTS humansa_medical_service CASCADE;

-- Create medical service table with correct schema
CREATE TABLE humansa_medical_service (
    service_code VARCHAR(20) PRIMARY KEY DEFAULT 'MS' || nextval('humansa_medical_service_seq'),
    clinic_code VARCHAR(10) REFERENCES humansa_clinic(clinic_code),
    service_name VARCHAR(200) NOT NULL,
    name VARCHAR(200), -- Alias for service_name for compatibility
    price DECIMAL(10,2),
    duration_minutes INTEGER DEFAULT 30,
    service_type VARCHAR(100),
    description TEXT,
    department VARCHAR(100),
    price_range_min DECIMAL(10,2),
    price_range_max DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create sequence for service codes
CREATE SEQUENCE IF NOT EXISTS humansa_medical_service_seq START 1000;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_medical_service_name ON humansa_medical_service(service_name);
CREATE INDEX IF NOT EXISTS idx_medical_service_clinic ON humansa_medical_service(clinic_code);
CREATE INDEX IF NOT EXISTS idx_medical_service_type ON humansa_medical_service(service_type);

-- Update name column to match service_name
CREATE OR REPLACE FUNCTION update_service_name()
RETURNS TRIGGER AS $$
BEGIN
    NEW.name := NEW.service_name;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_service_name
BEFORE INSERT OR UPDATE ON humansa_medical_service
FOR EACH ROW
EXECUTE FUNCTION update_service_name();