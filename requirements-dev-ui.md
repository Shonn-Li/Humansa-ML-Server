# Test Management Dashboard - Requirements Document

## Overview
A comprehensive web-based test management system for the YouWo AI ML Server that provides centralized control over test execution, monitoring, and analysis.

## System Architecture

### Components
1. **ML Server** (Port 6001+): Test instance of the ML server
2. **Dashboard Backend** (Port 6002): FastAPI server for test management
3. **Dashboard Frontend**: React-based UI for test interaction
4. **Database**: PostgreSQL schema for test tracking (in test${digit} database)

### Port Management
- Development server detection: Read current ML server port
- Dynamic port calculation: `base_port + digit`
- Test database mapping: Port 6001 → test1, Port 6003 → test3, etc.

## Functional Requirements

### 1. Environment Management
- **Server Discovery**
  - Auto-detect running ML servers
  - Display server status and configuration
  - Show port and database mappings

- **Server Control**
  - Launch new ML server instances
  - Execute in new terminal windows
  - Configure environment variables
  - Monitor server health

### 2. Job Management
- **Job Creation**
  - Name and describe test jobs
  - Select test suites or individual tests
  - Configure execution parameters
  - Save as templates for reuse

- **Test Selection**
  - Browse available test suites
  - Search and filter tests
  - Preview test configurations
  - Batch selection support

### 3. Test Execution
- **Parallel Processing**
  - Configure worker count
  - Smart test batching
  - Load distribution
  - Conflict prevention

- **Real-time Monitoring**
  - Live progress updates
  - Log streaming
  - Performance metrics
  - Error notifications

### 4. Results Analysis
- **Drill-down Navigation**
  - Jobs → Test Runs → Test Suites → Individual Tests → Detailed Logs
  - Each level shows relevant metrics and status

- **Detailed Views**
  - Test case configuration
  - Request/response payloads
  - Server logs (isolated by test)
  - Context snapshots
  - Performance metrics

### 5. Test Standardization

#### Test Format Schema
```json
{
  "id": "string",                    // Unique test identifier
  "name": "string",                  // Human-readable name
  "suite": "string",                 // Test suite category
  "type": "single|multi_turn",       // Test type
  "priority": "number",              // 1-5 priority level
  "tags": ["string"],                // Categorization tags
  
  "config": {
    "timeout": "number",             // Max execution time (seconds)
    "retries": "number",             // Retry count on failure
    "parallel_safe": "boolean",      // Can run in parallel
    "requirements": ["string"]       // Required server features
  },
  
  "setup": {
    "user_context": {},              // User profile data
    "previous_turns": [{             // For multi-turn tests
      "role": "user|assistant",
      "content": "string"
    }],
    "environment": {}                // Environment overrides
  },
  
  "execution": {
    "endpoint": "string",            // API endpoint
    "method": "POST|GET",            // HTTP method
    "headers": {},                   // Request headers
    "payload": {}                    // Request body
  },
  
  "expectations": {
    "response": {
      "status_code": "number",
      "headers": {},
      "output_contains": ["string"],
      "output_excludes": ["string"],
      "output_regex": ["string"],
      "min_length": "number",
      "max_length": "number",
      "custom_validators": ["string"]
    },
    
    "reasoning": {
      "steps_min": "number",
      "steps_max": "number",
      "contains_keywords": ["string"],
      "excludes_keywords": ["string"],
      "tool_calls": ["string"],
      "tool_results_contain": {}
    },
    
    "agents": {
      "touched": ["string"],
      "not_touched": ["string"],
      "call_order": ["string"],
      "max_agents": "number"
    },
    
    "context": {
      "mem0": {
        "should_store": ["string"],
        "should_retrieve": ["string"],
        "memory_count": "number"
      },
      "workflow": {
        "state_changes": {},
        "final_state": {},
        "events_emitted": ["string"]
      }
    },
    
    "server_logs": {
      "contains": ["string"],
      "excludes": ["string"],
      "regex_matches": ["string"],
      "log_levels": {
        "ERROR": "=0",
        "WARNING": "<=2",
        "INFO": ">=5"
      }
    },
    
    "performance": {
      "response_time_max": "number",
      "memory_usage_max": "string",
      "token_usage_max": "number",
      "database_queries_max": "number"
    }
  },
  
  "cleanup": {
    "commands": ["string"],          // Cleanup commands
    "reset_context": "boolean"       // Reset user context
  }
}
```

## Technical Requirements

### Backend (FastAPI)

#### API Endpoints
```
# Environment Management
GET    /api/environments              # List all environments
POST   /api/environments              # Create new environment
GET    /api/environments/{id}         # Get environment details
POST   /api/environments/{id}/start   # Start ML server
POST   /api/environments/{id}/stop    # Stop ML server
GET    /api/environments/{id}/health  # Check server health

# Job Management  
GET    /api/jobs                      # List all jobs
POST   /api/jobs                      # Create new job
GET    /api/jobs/{id}                 # Get job details
PUT    /api/jobs/{id}                 # Update job
DELETE /api/jobs/{id}                 # Delete job
POST   /api/jobs/{id}/execute         # Execute job

# Test Management
GET    /api/tests                     # List all tests
GET    /api/tests/{id}                # Get test details
POST   /api/tests/validate            # Validate test JSON
GET    /api/tests/discover            # Auto-discover tests

# Execution Management
GET    /api/runs                      # List all runs
GET    /api/runs/{id}                 # Get run details
GET    /api/runs/{id}/progress        # Get real-time progress
POST   /api/runs/{id}/cancel          # Cancel running job
GET    /api/runs/{id}/logs            # Stream logs

# Results Management
GET    /api/results                   # List all results
GET    /api/results/{run_id}          # Get run results
GET    /api/results/{run_id}/suite/{suite}  # Get suite results
GET    /api/results/{run_id}/test/{test}    # Get test details
GET    /api/results/analytics         # Get analytics data

# Export
POST   /api/export/pdf                # Export PDF report
POST   /api/export/csv                # Export CSV data
POST   /api/export/json               # Export JSON data
```

#### WebSocket Events
```
# Real-time updates via WebSocket
/ws/runs/{run_id}
  - run.started
  - run.progress
  - test.started
  - test.completed
  - test.failed
  - log.message
  - run.completed
```

### Frontend (React)

#### Component Structure
```
src/
├── components/
│   ├── layout/
│   │   ├── Dashboard.tsx
│   │   ├── Sidebar.tsx
│   │   └── Header.tsx
│   │
│   ├── environments/
│   │   ├── EnvironmentList.tsx
│   │   ├── EnvironmentCard.tsx
│   │   ├── ServerLauncher.tsx
│   │   └── HealthIndicator.tsx
│   │
│   ├── jobs/
│   │   ├── JobList.tsx
│   │   ├── JobCreator.tsx
│   │   ├── TestSelector.tsx
│   │   ├── TestTree.tsx
│   │   └── JobTemplates.tsx
│   │
│   ├── execution/
│   │   ├── ExecutionMonitor.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── ParallelWorkers.tsx
│   │   ├── LogStream.tsx
│   │   └── MetricsDisplay.tsx
│   │
│   ├── results/
│   │   ├── ResultsExplorer.tsx
│   │   ├── RunHistory.tsx
│   │   ├── SuiteResults.tsx
│   │   ├── TestDetails.tsx
│   │   ├── LogViewer.tsx
│   │   └── PerformanceCharts.tsx
│   │
│   └── common/
│       ├── DataTable.tsx
│       ├── SearchBar.tsx
│       ├── FilterPanel.tsx
│       └── ExportMenu.tsx
│
├── hooks/
│   ├── useWebSocket.ts
│   ├── useEnvironments.ts
│   ├── useTestExecution.ts
│   └── useResults.ts
│
├── services/
│   ├── api.ts
│   ├── websocket.ts
│   ├── testParser.ts
│   └── exportService.ts
│
└── utils/
    ├── formatters.ts
    ├── validators.ts
    └── constants.ts
```

### Database Schema

```sql
-- Test management schema
CREATE SCHEMA IF NOT EXISTS test_management;

-- Environments table
CREATE TABLE test_management.environments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    base_port INTEGER NOT NULL,
    digit INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'stopped',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat TIMESTAMP,
    UNIQUE(base_port, digit)
);

-- Jobs table
CREATE TABLE test_management.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    test_items JSONB NOT NULL, -- Array of test IDs or suite names
    config JSONB DEFAULT '{}',
    is_template BOOLEAN DEFAULT FALSE,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Test runs table
CREATE TABLE test_management.runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES test_management.jobs(id),
    environment_id UUID REFERENCES test_management.environments(id),
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    skipped_tests INTEGER DEFAULT 0,
    execution_config JSONB DEFAULT '{}',
    summary JSONB DEFAULT '{}'
);

-- Test results table
CREATE TABLE test_management.results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES test_management.runs(id),
    test_id VARCHAR(255) NOT NULL,
    suite_name VARCHAR(255),
    test_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    execution_time FLOAT,
    error_message TEXT,
    assertions JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    INDEX idx_run_id (run_id),
    INDEX idx_status (status)
);

-- Test logs table (overview logs)
CREATE TABLE test_management.logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id UUID REFERENCES test_management.results(id),
    log_type VARCHAR(50), -- 'execution', 'server', 'error'
    level VARCHAR(20),
    message TEXT,
    metadata JSONB DEFAULT '{}',
    thread_id VARCHAR(50), -- For parallel execution tracking
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_result_id (result_id),
    INDEX idx_timestamp (timestamp)
);

-- Test case logs table (detailed per-test logs)
CREATE TABLE test_management.test_case_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id UUID REFERENCES test_management.results(id),
    request JSONB NOT NULL,
    response JSONB,
    server_logs TEXT,
    context_snapshot JSONB,
    performance_metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_result_id (result_id)
);

-- Test definitions table (cached test configurations)
CREATE TABLE test_management.test_definitions (
    id VARCHAR(255) PRIMARY KEY,
    suite VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    priority INTEGER DEFAULT 1,
    tags TEXT[],
    config JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_suite (suite),
    INDEX idx_tags (tags)
);
```

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. Create database schema
2. Set up FastAPI backend structure
3. Implement environment detection logic
4. Create basic React app scaffold
5. Establish WebSocket connection

### Phase 2: Test Standardization (Week 2)
1. Define complete test schema
2. Create validation system
3. Convert existing tests to JSON
4. Build test discovery system
5. Implement test parser

### Phase 3: Core Features (Week 3-4)
1. Environment management UI
2. Job creation and management
3. Test execution engine
4. Parallel execution coordinator
5. Real-time progress tracking

### Phase 4: Results & Analysis (Week 5)
1. Results explorer UI
2. Drill-down navigation
3. Log viewer with filtering
4. Performance analytics
5. Export functionality

### Phase 5: Polish & Optimization (Week 6)
1. UI/UX improvements
2. Performance optimization
3. Error handling
4. Documentation
5. Testing

## Non-Functional Requirements

### Performance
- Support 1000+ concurrent test executions
- Real-time updates with <100ms latency
- Handle logs up to 10MB per test
- Page load time <2 seconds

### Scalability
- Support multiple ML server instances
- Horizontal scaling for parallel execution
- Efficient log storage and retrieval
- Pagination for large result sets

### Reliability
- Graceful handling of ML server crashes
- Resume interrupted test runs
- Data consistency during parallel execution
- Automatic cleanup of stale resources

### Usability
- Intuitive navigation
- Clear status indicators
- Helpful error messages
- Keyboard shortcuts
- Responsive design

### Security
- Input validation
- SQL injection prevention
- XSS protection
- Rate limiting
- Audit logging

## Success Metrics
1. Reduce test execution time by 80% through parallelization
2. Provide test results within 2 clicks from dashboard
3. Support running 100+ tests in parallel
4. Achieve 99% uptime for dashboard
5. Enable test debugging in <1 minute