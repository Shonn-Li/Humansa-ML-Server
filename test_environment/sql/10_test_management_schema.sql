-- Test Management Dashboard Schema
-- This schema tracks all test execution, results, and logs for the ML server testing
-- Used by the Test Management Dashboard UI (port 6002)

-- Create schema
CREATE SCHEMA IF NOT EXISTS test_management;

-- Environments table: Track ML server instances
CREATE TABLE IF NOT EXISTS test_management.environments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    base_port INTEGER NOT NULL,
    digit INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'stopped', -- stopped, starting, running, error
    pid INTEGER, -- Process ID when running
    config JSONB DEFAULT '{}', -- Environment variables and settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat TIMESTAMP,
    error_message TEXT,
    UNIQUE(base_port, digit)
);

-- Jobs table: Test execution jobs
CREATE TABLE IF NOT EXISTS test_management.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    test_items JSONB NOT NULL, -- Array of {type: 'suite'|'test', id: 'string'}
    config JSONB DEFAULT '{}', -- {parallel_workers: 4, timeout: 300, etc.}
    is_template BOOLEAN DEFAULT FALSE,
    created_by VARCHAR(255) DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Test runs table: Execution instances of jobs
CREATE TABLE IF NOT EXISTS test_management.runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES test_management.jobs(id) ON DELETE CASCADE,
    environment_id UUID REFERENCES test_management.environments(id),
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    skipped_tests INTEGER DEFAULT 0,
    execution_config JSONB DEFAULT '{}',
    summary JSONB DEFAULT '{}', -- Overall statistics and metadata
    error_message TEXT
);

-- Test results table: Individual test execution results
CREATE TABLE IF NOT EXISTS test_management.results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES test_management.runs(id) ON DELETE CASCADE,
    test_id VARCHAR(255) NOT NULL, -- e.g., 'APT_001'
    suite_name VARCHAR(255),
    test_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL, -- passed, failed, skipped, error
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    execution_time FLOAT, -- in seconds
    error_message TEXT,
    assertions JSONB DEFAULT '{}', -- {response_valid: true, keywords_found: false, etc.}
    metrics JSONB DEFAULT '{}', -- {response_time: 1.5, tokens_used: 150, etc.}
    worker_id VARCHAR(50) -- For parallel execution tracking
);

-- Indexes for results table
CREATE INDEX IF NOT EXISTS idx_results_run_id ON test_management.results(run_id);
CREATE INDEX IF NOT EXISTS idx_results_status ON test_management.results(status);
CREATE INDEX IF NOT EXISTS idx_results_test_id ON test_management.results(test_id);

-- Test logs table: General execution logs
CREATE TABLE IF NOT EXISTS test_management.logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id UUID REFERENCES test_management.results(id) ON DELETE CASCADE,
    log_type VARCHAR(50), -- 'execution', 'server', 'error', 'debug'
    level VARCHAR(20), -- 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    message TEXT,
    metadata JSONB DEFAULT '{}',
    thread_id VARCHAR(50), -- For parallel execution tracking
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for logs table
CREATE INDEX IF NOT EXISTS idx_logs_result_id ON test_management.logs(result_id);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON test_management.logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_level ON test_management.logs(level);

-- Test case logs table: Detailed per-test execution data
CREATE TABLE IF NOT EXISTS test_management.test_case_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id UUID REFERENCES test_management.results(id) ON DELETE CASCADE,
    request JSONB NOT NULL, -- Full API request
    response JSONB, -- Full API response
    server_logs TEXT, -- Captured server logs during test
    context_snapshot JSONB, -- Memory/workflow context at test time
    performance_metrics JSONB, -- Detailed performance data
    validation_details JSONB, -- Detailed validation results
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for test case logs
CREATE INDEX IF NOT EXISTS idx_test_case_logs_result_id ON test_management.test_case_logs(result_id);

-- Test definitions table: Cached test configurations
CREATE TABLE IF NOT EXISTS test_management.test_definitions (
    id VARCHAR(255) PRIMARY KEY, -- e.g., 'APT_001'
    suite VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'single', 'multi_turn'
    priority INTEGER DEFAULT 1,
    tags TEXT[],
    config JSONB NOT NULL, -- Full test configuration
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for test definitions
CREATE INDEX IF NOT EXISTS idx_test_defs_suite ON test_management.test_definitions(suite);
CREATE INDEX IF NOT EXISTS idx_test_defs_tags ON test_management.test_definitions USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_test_defs_active ON test_management.test_definitions(is_active);

-- Test suites table: Group tests into suites
CREATE TABLE IF NOT EXISTS test_management.test_suites (
    id VARCHAR(255) PRIMARY KEY, -- e.g., 'appointment'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    test_ids TEXT[], -- Array of test IDs in this suite
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Execution queue table: For managing parallel execution
CREATE TABLE IF NOT EXISTS test_management.execution_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES test_management.runs(id) ON DELETE CASCADE,
    test_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, assigned, running, completed
    worker_id VARCHAR(50),
    priority INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes for execution queue
CREATE INDEX IF NOT EXISTS idx_queue_run_id ON test_management.execution_queue(run_id);
CREATE INDEX IF NOT EXISTS idx_queue_status ON test_management.execution_queue(status);
CREATE INDEX IF NOT EXISTS idx_queue_priority ON test_management.execution_queue(priority DESC);

-- Analytics table: Aggregated test performance data
CREATE TABLE IF NOT EXISTS test_management.analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    total_runs INTEGER DEFAULT 0,
    passed_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    avg_execution_time FLOAT,
    min_execution_time FLOAT,
    max_execution_time FLOAT,
    error_types JSONB DEFAULT '{}', -- {timeout: 5, assertion: 3, etc.}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(test_id, date)
);

-- Index for analytics
CREATE INDEX IF NOT EXISTS idx_analytics_test_date ON test_management.analytics(test_id, date);

-- Functions and triggers

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION test_management.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update trigger to jobs table
CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON test_management.jobs
    FOR EACH ROW
    EXECUTE FUNCTION test_management.update_updated_at();

-- Apply update trigger to test definitions table
CREATE TRIGGER update_test_defs_updated_at
    BEFORE UPDATE ON test_management.test_definitions
    FOR EACH ROW
    EXECUTE FUNCTION test_management.update_updated_at();

-- Apply update trigger to test suites table
CREATE TRIGGER update_test_suites_updated_at
    BEFORE UPDATE ON test_management.test_suites
    FOR EACH ROW
    EXECUTE FUNCTION test_management.update_updated_at();

-- Function to calculate run statistics
CREATE OR REPLACE FUNCTION test_management.update_run_statistics(p_run_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE test_management.runs
    SET 
        total_tests = (SELECT COUNT(*) FROM test_management.results WHERE run_id = p_run_id),
        passed_tests = (SELECT COUNT(*) FROM test_management.results WHERE run_id = p_run_id AND status = 'passed'),
        failed_tests = (SELECT COUNT(*) FROM test_management.results WHERE run_id = p_run_id AND status = 'failed'),
        skipped_tests = (SELECT COUNT(*) FROM test_management.results WHERE run_id = p_run_id AND status = 'skipped')
    WHERE id = p_run_id;
END;
$$ LANGUAGE plpgsql;

-- Function to update analytics
CREATE OR REPLACE FUNCTION test_management.update_analytics(p_test_id VARCHAR(255), p_date DATE)
RETURNS VOID AS $$
BEGIN
    INSERT INTO test_management.analytics (test_id, date, total_runs, passed_runs, failed_runs, avg_execution_time, min_execution_time, max_execution_time)
    SELECT 
        p_test_id,
        p_date,
        COUNT(*),
        COUNT(*) FILTER (WHERE status = 'passed'),
        COUNT(*) FILTER (WHERE status = 'failed'),
        AVG(execution_time),
        MIN(execution_time),
        MAX(execution_time)
    FROM test_management.results r
    JOIN test_management.runs run ON r.run_id = run.id
    WHERE r.test_id = p_test_id
    AND DATE(r.started_at) = p_date
    ON CONFLICT (test_id, date) DO UPDATE SET
        total_runs = EXCLUDED.total_runs,
        passed_runs = EXCLUDED.passed_runs,
        failed_runs = EXCLUDED.failed_runs,
        avg_execution_time = EXCLUDED.avg_execution_time,
        min_execution_time = EXCLUDED.min_execution_time,
        max_execution_time = EXCLUDED.max_execution_time;
END;
$$ LANGUAGE plpgsql;

-- Sample data for testing
INSERT INTO test_management.environments (name, base_port, digit, status) VALUES
    ('Test Environment 1', 6000, 1, 'stopped'),
    ('Test Environment 2', 6000, 2, 'stopped'),
    ('Test Environment 3', 6000, 3, 'stopped')
ON CONFLICT DO NOTHING;

-- Grant permissions (adjust user as needed)
GRANT ALL ON SCHEMA test_management TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA test_management TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA test_management TO postgres;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA test_management TO postgres;