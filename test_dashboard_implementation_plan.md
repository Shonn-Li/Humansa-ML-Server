# Test Dashboard Implementation Plan

## Critical Corrections

1. **Database Location**: 
   - Test management tables go in the ACTUAL ML server database (e.g., `test5` for port 5005)
   - NOT in a separate test environment database
   - Migration only needs to run once per environment

2. **Port Configuration**:
   - Production always uses 5432 for PostgreSQL
   - ML Server uses 5000 + digit (e.g., 5005 for digit 5)
   - Dashboard connects to the same database as the ML server

## Phase 1: Test Discovery & Conversion (10 Sub-Agents)

### Sub-Agent 1: Test Discovery Agent
**Task**: Scan all test files and create comprehensive inventory
- Find all test files (Python scripts)
- Identify test patterns and structures
- Create manifest of all tests with metadata
- Output: `test_inventory.json`

### Sub-Agent 2-5: Suite Categorization Agents (4 agents, parallel)
**Tasks**: Categorize tests into proper suites
- Agent 2: Appointment & Form tests
- Agent 3: Medical consultation & Emergency tests  
- Agent 4: Product & Identity tests
- Agent 5: Multi-turn & Edge case tests
**Output**: Categorized test lists per suite

### Sub-Agent 6-10: Test Conversion Agents (5 agents, parallel)
**Tasks**: Convert Python tests to JSON format
- Each agent handles ~20% of tests
- Parse Python test structure
- Extract expectations and metadata
- Generate standardized JSON files
- Validate against schema
**Output**: JSON test files in `test_definitions/`

## Phase 2: UI Implementation (5 Sub-Agents)

### Sub-Agent 11: Environment Manager UI
**Components**:
- ServerList.tsx - Display running ML servers
- ServerLauncher.tsx - Start new ML instances
- PortDetector.tsx - Auto-detect server ports
- HealthMonitor.tsx - Real-time health status

### Sub-Agent 12: Job Management UI
**Components**:
- JobCreator.tsx - Create/edit test jobs
- TestSelector.tsx - Browse and select tests
- BatchOptimizer.tsx - Optimize test batching
- JobTemplates.tsx - Save/load job templates

### Sub-Agent 13: Execution Monitor UI
**Components**:
- ExecutionDashboard.tsx - Main execution view
- ProgressTracker.tsx - Real-time progress
- LogStream.tsx - Live log viewer
- WorkerStatus.tsx - Parallel worker monitoring

### Sub-Agent 14: Results Explorer UI
**Components**:
- ResultsGrid.tsx - Test results overview
- DrillDownView.tsx - Hierarchical navigation
- TestDetails.tsx - Individual test analysis
- LogViewer.tsx - Detailed log inspection

### Sub-Agent 15: Analytics & Export UI
**Components**:
- PerformanceCharts.tsx - Metrics visualization
- TrendAnalysis.tsx - Historical trends
- ExportDialog.tsx - Export functionality
- ReportBuilder.tsx - Custom report generation

## Phase 3: Backend Implementation (3 Sub-Agents)

### Sub-Agent 16: Core Backend Services
- Database models and migrations
- WebSocket connection manager
- Test execution engine
- Parallel worker coordinator

### Sub-Agent 17: API Implementation
- All REST endpoints
- Request/response validation
- Error handling
- Authentication (if needed)

### Sub-Agent 18: Integration Services
- ML server communication
- Log capture and parsing
- Context snapshot service
- Performance monitoring

## Execution Strategy

### Step 1: Fix Database Configuration
```python
# Correct configuration
DB_PORT = 5432  # Production PostgreSQL
ML_SERVER_PORT = 5000 + DIGIT  # e.g., 5005
DB_NAME = f"test{DIGIT}"  # e.g., test5
```

### Step 2: Run Migrations Once
```sql
-- Run in the actual ML server database (e.g., test5)
-- NOT in a separate test environment
CREATE SCHEMA IF NOT EXISTS test_management;
-- ... rest of schema
```

### Step 3: Parallel Execution Plan
1. Launch Sub-Agents 1-10 for test conversion (parallel)
2. Launch Sub-Agents 11-15 for UI development (parallel)
3. Launch Sub-Agents 16-18 for backend (sequential)

## Expected Deliverables

### From Test Conversion Agents:
- Complete test inventory
- 200+ JSON test files
- Test validation reports
- Suite organization

### From UI Agents:
- Complete React application
- 20+ UI components
- Real-time WebSocket integration
- Responsive design

### From Backend Agents:
- FastAPI server
- Complete API implementation
- Database integration
- Execution engine

## Timeline
- Test Conversion: 2-3 hours with parallel agents
- UI Development: 4-5 hours with parallel agents
- Backend Development: 3-4 hours
- Integration & Testing: 2-3 hours

Total: ~12-15 hours with parallel execution