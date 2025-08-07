// Common types used across the application

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface BaseEntity {
  id: string;
  createdAt: string;
  updatedAt: string;
}

// Test related types
export interface TestCase extends BaseEntity {
  name: string;
  description?: string;
  suite: string;
  category: string;
  type: 'single' | 'multi_turn' | 'performance' | 'integration';
  tags: string[];
  execution: {
    endpoint: string;
    method: 'GET' | 'POST' | 'PUT' | 'DELETE';
    payload?: any;
    headers?: Record<string, string>;
    timeout?: number;
  };
  expectations: {
    response?: {
      status_code?: number;
      output_contains?: string[];
      output_not_contains?: string[];
      response_format?: 'json' | 'text' | 'stream';
    };
    performance?: {
      response_time_max?: number;
      memory_usage_max?: number;
    };
    reasoning?: {
      tool_calls?: string[];
      reasoning_contains?: string[];
    };
  };
  metadata?: Record<string, any>;
}

export interface TestResult extends BaseEntity {
  testCaseId: string;
  runId: string;
  status: 'pending' | 'running' | 'passed' | 'failed' | 'skipped' | 'timeout';
  startTime?: string;
  endTime?: string;
  duration?: number;
  response?: any;
  error?: string;
  logs?: string[];
  metrics?: {
    responseTime: number;
    memoryUsage?: number;
    cpuUsage?: number;
  };
  assertions?: {
    passed: number;
    failed: number;
    details: Array<{
      assertion: string;
      passed: boolean;
      message?: string;
    }>;
  };
}

// Job Management types
export interface Job extends BaseEntity {
  name: string;
  description?: string;
  testCases: string[]; // Array of test case IDs
  configuration: JobConfiguration;
  templateId?: string;
  status: 'draft' | 'active' | 'archived';
  lastRunId?: string;
  runCount: number;
  tags: string[];
}

export interface JobConfiguration {
  execution: {
    parallelWorkers: number;
    timeout: number;
    retryCount: number;
    failFast: boolean;
    randomizeOrder: boolean;
  };
  environment: {
    serverId?: string;
    variables?: Record<string, string>;
  };
  notifications: {
    onCompletion: boolean;
    onFailure: boolean;
    webhookUrl?: string;
    emailRecipients?: string[];
  };
  scheduling?: {
    enabled: boolean;
    cron?: string;
    timezone?: string;
  };
}

export interface JobTemplate extends BaseEntity {
  name: string;
  description?: string;
  configuration: JobConfiguration;
  defaultTestCases?: string[];
  category: string;
  isPublic: boolean;
  createdBy: string;
  usageCount: number;
  tags: string[];
}

export interface JobRun extends BaseEntity {
  jobId: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  startTime?: string;
  endTime?: string;
  duration?: number;
  configuration: JobConfiguration;
  testCases: string[];
  results: TestResult[];
  metrics: {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
    pending: number;
    successRate: number;
    averageResponseTime: number;
  };
  logs?: string[];
  triggeredBy: 'manual' | 'schedule' | 'webhook' | 'api';
  triggeredByUser?: string;
}

// Test selection and filtering
export interface TestFilter {
  suites?: string[];
  categories?: string[];
  types?: string[];
  tags?: string[];
  search?: string;
  status?: string[];
}

export interface TestGroup {
  id: string;
  name: string;
  description?: string;
  tests: TestCase[];
  estimatedDuration: number;
  category: string;
}

// Batch optimization
export interface BatchAnalysis {
  totalTests: number;
  estimatedDuration: number;
  recommendedBatches: BatchRecommendation[];
  parallelizationOptions: ParallelizationOption[];
  dependencies: TestDependency[];
  warnings: string[];
}

export interface BatchRecommendation {
  id: string;
  name: string;
  tests: string[]; // Test case IDs
  estimatedDuration: number;
  workers: number;
  reasoning: string;
  dependencies: string[]; // Batch IDs this depends on
}

export interface ParallelizationOption {
  workers: number;
  estimatedDuration: number;
  efficiency: number; // 0-100%
  resourceUsage: {
    cpu: number;
    memory: number;
    network: number;
  };
  recommendation: 'optimal' | 'conservative' | 'aggressive';
}

export interface TestDependency {
  testId: string;
  dependsOn: string[];
  type: 'data' | 'state' | 'resource' | 'sequence';
  description: string;
}

// Environment and server management
export interface Environment extends BaseEntity {
  name: string;
  description?: string;
  serverUrl: string;
  port: number;
  status: 'running' | 'stopped' | 'error' | 'unknown';
  version?: string;
  healthCheck?: {
    lastChecked: string;
    status: 'healthy' | 'unhealthy' | 'warning';
    responseTime: number;
    message?: string;
  };
  configuration?: Record<string, any>;
}

// Export and import
export interface ExportOptions {
  format: 'json' | 'csv' | 'pdf' | 'xlsx';
  includeResults: boolean;
  includeLogs: boolean;
  dateRange?: {
    start: string;
    end: string;
  };
  filters?: TestFilter;
}

export interface ImportResult {
  success: boolean;
  imported: number;
  skipped: number;
  errors: Array<{
    line: number;
    message: string;
    data?: any;
  }>;
}

// WebSocket types for real-time updates
export type MessageType = 'run_update' | 'test_update' | 'log_update' | 'metric_update' | 'log_entry' | 'test_completed' | 'worker_update';

export interface WebSocketMessage {
  type: MessageType;
  runId?: string;
  testId?: string;
  data: any;
  timestamp: string;
}

export interface RunUpdate {
  status: JobRun['status'];
  metrics: JobRun['metrics'];
  currentTest?: string;
  progress: number; // 0-100%
}

export interface TestUpdate {
  testId: string;
  status: TestResult['status'];
  result?: Partial<TestResult>;
}

// UI State types
export interface UIState {
  selectedTests: Set<string>;
  activeFilters: TestFilter;
  viewMode: 'list' | 'grid' | 'tree';
  sortBy: 'name' | 'category' | 'duration' | 'status';
  sortOrder: 'asc' | 'desc';
}

export interface TreeNode<T = any> {
  id: string;
  label: string;
  children?: TreeNode<T>[];
  data?: T;
  expanded?: boolean;
  selected?: boolean;
  disabled?: boolean;
  icon?: string;
  badge?: {
    text: string;
    variant: 'primary' | 'secondary' | 'success' | 'warning' | 'error';
  };
}

// Additional type aliases for backward compatibility
export type TestRun = JobRun;
export type TestJob = Job;
export type TestSuite = TestGroup;
export type FilterOptions = TestFilter;
export type SortOptions = Pick<UIState, 'sortBy' | 'sortOrder'>;
export type PaginationOptions = {
  page: number;
  limit: number;
};

export enum TestStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  PASSED = 'passed',
  FAILED = 'failed',
  SKIPPED = 'skipped',
  TIMEOUT = 'timeout'
}

export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error'
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  source?: string;
  metadata?: Record<string, any>;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}