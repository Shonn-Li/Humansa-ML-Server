-- Test Management Schema for Test Dashboard
-- Applied to main database (port 5432, database test${DIGIT})
-- This schema stores test definitions, jobs, runs, and results

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS test_management;

-- Set search path
SET search_path TO test_management;

-- Jobs table
CREATE TABLE IF NOT EXISTS test_management.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    test_ids TEXT[],
    tests JSONB,
    test_items JSONB,
    config JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(50) DEFAULT 'normal',
    workers INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    progress JSONB,
    run_id UUID,
    recurring VARCHAR(255),
    tags TEXT[],
    total_tests INTEGER,
    completed_tests INTEGER,
    failed_tests INTEGER
);

-- Runs table
CREATE TABLE IF NOT EXISTS test_management.runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES test_management.jobs(id),
    status VARCHAR(50),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    execution_config JSONB,
    total_tests INTEGER,
    passed_tests INTEGER,
    failed_tests INTEGER,
    skipped_tests INTEGER,
    summary JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Results table
CREATE TABLE IF NOT EXISTS test_management.results (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    test_id VARCHAR(255) NOT NULL,
    suite_name VARCHAR(100),
    test_name VARCHAR(255),
    status VARCHAR(50),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    execution_time FLOAT,
    instance_id INTEGER,
    request JSONB,
    response JSONB,
    expected JSONB,
    actual JSONB,
    validation_results JSONB,
    error TEXT,
    error_type VARCHAR(100),
    retry_count INTEGER DEFAULT 0,
    output JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Logs table
CREATE TABLE IF NOT EXISTS test_management.logs (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    test_id VARCHAR(255),
    level VARCHAR(20),
    message TEXT,
    context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Instances table
CREATE TABLE IF NOT EXISTS test_management.instances (
    id INTEGER PRIMARY KEY,
    port INTEGER NOT NULL,
    status VARCHAR(50),
    last_health_check TIMESTAMP,
    current_test_id VARCHAR(255),
    total_tests_executed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create update trigger function
CREATE OR REPLACE FUNCTION test_management.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add update triggers
DROP TRIGGER IF EXISTS update_jobs_updated_at ON test_management.jobs;
CREATE TRIGGER update_jobs_updated_at 
    BEFORE UPDATE ON test_management.jobs 
    FOR EACH ROW 
    EXECUTE FUNCTION test_management.update_updated_at_column();

DROP TRIGGER IF EXISTS update_runs_updated_at ON test_management.runs;
CREATE TRIGGER update_runs_updated_at 
    BEFORE UPDATE ON test_management.runs 
    FOR EACH ROW 
    EXECUTE FUNCTION test_management.update_updated_at_column();

DROP TRIGGER IF EXISTS update_instances_updated_at ON test_management.instances;
CREATE TRIGGER update_instances_updated_at 
    BEFORE UPDATE ON test_management.instances 
    FOR EACH ROW 
    EXECUTE FUNCTION test_management.update_updated_at_column();

-- Grant permissions (adjust user as needed)
GRANT ALL ON SCHEMA test_management TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA test_management TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA test_management TO postgres;