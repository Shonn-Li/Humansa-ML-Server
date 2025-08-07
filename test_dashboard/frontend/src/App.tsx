import React, { useState, useEffect } from 'react';
import InstanceControl from './components/InstanceControl';

interface Test {
  id: string;
  name: string;
  suite: string;
  type: string;
  priority: number;
  tags: string[];
  file_path?: string;
  created_at?: string;
  updated_at?: string;
  config?: any;
  setup?: any;
  execution?: any;
  expectations?: any;
  cleanup?: any;
}

interface Job {
  id: string;
  name: string;
  description?: string;
  status: string;
  priority: string;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  scheduled_at?: string;
  tests: Array<{
    test_id: string;
    suite?: string;
    priority_override?: number;
  }>;
  config: {
    execution_mode: string;
    max_parallel_workers: number;
    timeout_per_test: number;
    retry_failed_tests: boolean;
    max_retries: number;
    continue_on_failure: boolean;
  };
  total_tests?: number;
  completed_tests?: number;
  failed_tests?: number;
  run_id?: string;
}

interface TestSuite {
  id: string;
  name: string;
  test_ids: string[];
  created_at: string;
  description?: string;
}

type ViewType = 'dashboard' | 'tests' | 'jobs' | 'suites' | 'results';

function App() {
  const [currentView, setCurrentView] = useState<ViewType>('dashboard');
  const [tests, setTests] = useState<Test[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [testSuites, setTestSuites] = useState<TestSuite[]>([]);
  const [selectedTests, setSelectedTests] = useState<Set<string>>(new Set());
  const [selectedTest, setSelectedTest] = useState<Test | null>(null);
  const [loading, setLoading] = useState(true);
  const [showSuiteModal, setShowSuiteModal] = useState(false);
  const [suiteFormData, setSuiteFormData] = useState({ name: '', description: '' });
  const [showFullJson, setShowFullJson] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [jobResults, setJobResults] = useState<any>({});
  const [selectedTestResult, setSelectedTestResult] = useState<any>(null);
  const [testLogs, setTestLogs] = useState<any>(null);
  const [systemInfo, setSystemInfo] = useState<any>(null);
  const [mlServerStatus, setMlServerStatus] = useState<{ running: boolean; enhanced_logging: boolean } | null>(null);

  // Fetch system information
  useEffect(() => {
    const fetchSystemInfo = async () => {
      try {
        const response = await fetch('http://localhost:6002/system-info');
        if (response.ok) {
          const data = await response.json();
          setSystemInfo(data);
        }
      } catch (error) {
        console.error('Failed to fetch system info:', error);
      }
    };
    fetchSystemInfo();
  }, []);

  useEffect(() => {
    console.log('App mounted, fetching data...');
    Promise.all([
      fetch('http://localhost:6002/api/tests?limit=1000').then(res => res.json()),
      fetch('http://localhost:6002/api/jobs').then(res => res.json()).catch(() => []),
      fetch('http://localhost:6002/system-info').then(res => res.json()).catch(() => null),
      fetch('http://localhost:6001/health').then(res => res.json()).catch(() => null)
    ]).then(([testsData, jobsData, sysInfo, mlStatus]) => {
      console.log('Data fetched:', testsData.length, 'tests');
      setTests(testsData);
      setJobs(jobsData);
      setSystemInfo(sysInfo);
      if (mlStatus) {
        setMlServerStatus({
          running: true,
          enhanced_logging: mlStatus.enhanced_logging || false
        });
      } else {
        setMlServerStatus({ running: false, enhanced_logging: false });
      }
      setLoading(false);
    }).catch(err => {
      console.error('Failed to fetch data:', err);
      setLoading(false);
    });
  }, []);

  // Auto-refresh jobs every 5 seconds ONLY if there are running jobs
  useEffect(() => {
    const hasRunningJobs = jobs.some(job => job.status === 'running');
    
    if (hasRunningJobs) {
      const interval = setInterval(async () => {
        try {
          const response = await fetch('http://localhost:6002/api/jobs');
          const jobsData = await response.json();
          setJobs(jobsData);
          
          // Only refresh selected job if it's still running
          if (selectedJob && selectedJob.status === 'running') {
            await fetchJobDetails(selectedJob.id);
          }
        } catch (err) {
          console.error('Failed to refresh jobs:', err);
        }
      }, 5000); // Check every 5 seconds
      
      return () => clearInterval(interval);
    }
  }, [jobs, selectedJob]);

  const fetchTestDetails = async (testId: string) => {
    try {
      const response = await fetch(`http://localhost:6002/api/tests/${testId}`);
      const fullTest = await response.json();
      setSelectedTest(fullTest);
    } catch (err) {
      console.error('Failed to fetch test details:', err);
    }
  };

  const fetchJobDetails = async (jobId: string) => {
    try {
      const response = await fetch(`http://localhost:6002/api/jobs/${jobId}`);
      const job = await response.json();
      setSelectedJob(job);
      
      // Clear previous results
      setJobResults({});
      
      // Also fetch run details if job has a run_id
      if (job.run_id) {
        const runResponse = await fetch(`http://localhost:6002/api/jobs/${jobId}/runs/${job.run_id}`);
        if (runResponse.ok) {
          const runData = await runResponse.json();
          console.log('Fetched run details:', runData);
          setJobResults(runData);
        } else {
          console.error('Failed to fetch run details:', runResponse.status);
        }
      } else {
        console.log('Job has no run_id yet');
      }
    } catch (err) {
      console.error('Failed to fetch job details:', err);
    }
  };

  const checkMlServerStatus = async () => {
    try {
      const response = await fetch('http://localhost:6001/health');
      if (response.ok) {
        const data = await response.json();
        setMlServerStatus({
          running: true,
          enhanced_logging: data.enhanced_logging || false
        });
      } else {
        setMlServerStatus({ running: false, enhanced_logging: false });
      }
    } catch (error) {
      setMlServerStatus({ running: false, enhanced_logging: false });
    }
  };

  const executeJob = async (jobId: string) => {
    try {
      const response = await fetch(`http://localhost:6002/api/jobs/${jobId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dry_run: false,
          environment_id: 1
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('Job execution started:', result);
        
        // Start polling for job updates
        let pollCount = 0;
        const pollInterval = setInterval(async () => {
          try {
            // Refresh jobs list
            const jobsResponse = await fetch('http://localhost:6002/api/jobs');
            const jobsData = await jobsResponse.json();
            setJobs(jobsData);
            
            // Also refresh the selected job if viewing it
            if (selectedJob && selectedJob.id === jobId) {
              await fetchJobDetails(jobId);
            }
            
            // Find the job in the updated list
            const updatedJob = jobsData.find((j: any) => j.id === jobId);
            
            // Stop polling if job is completed or after 60 seconds
            pollCount++;
            if (updatedJob && (updatedJob.status === 'completed' || updatedJob.status === 'failed') || pollCount > 30) {
              clearInterval(pollInterval);
            }
          } catch (err) {
            console.error('Failed to poll job status:', err);
          }
        }, 2000); // Poll every 2 seconds
      } else {
        const error = await response.text();
        alert('Failed to start job: ' + error);
      }
    } catch (err) {
      console.error('Failed to execute job:', err);
      alert('Failed to execute job');
    }
  };

  const stopJob = async (jobId: string) => {
    try {
      const response = await fetch(`http://localhost:6002/api/jobs/${jobId}/stop`, {
        method: 'POST'
      });
      
      if (response.ok) {
        alert('Job stopped');
        // Refresh jobs list
        const jobsResponse = await fetch('http://localhost:6002/api/jobs');
        const jobsData = await jobsResponse.json();
        setJobs(jobsData);
      }
    } catch (err) {
      console.error('Failed to stop job:', err);
    }
  };

  const handleSelectAll = () => {
    if (selectedTests.size === tests.length) {
      setSelectedTests(new Set());
    } else {
      setSelectedTests(new Set(tests.map(t => t.id)));
    }
  };

  const handleSelectSuite = (suite: string) => {
    const suiteTests = tests.filter(t => t.suite === suite);
    const suiteTestIds = suiteTests.map(t => t.id);
    const newSelected = new Set(selectedTests);
    
    // Check if all tests in this suite are selected
    const allSelected = suiteTestIds.every(id => selectedTests.has(id));
    
    if (allSelected) {
      // Deselect all in this suite
      suiteTestIds.forEach(id => newSelected.delete(id));
    } else {
      // Select all in this suite
      suiteTestIds.forEach(id => newSelected.add(id));
    }
    
    setSelectedTests(newSelected);
  };

  const handleSelectTest = (testId: string) => {
    const newSelected = new Set(selectedTests);
    if (newSelected.has(testId)) {
      newSelected.delete(testId);
    } else {
      newSelected.add(testId);
    }
    setSelectedTests(newSelected);
  };

  const handleCreateJob = async () => {
    if (selectedTests.size === 0) return;
    
    const payload = {
      name: `Manual Run - ${new Date().toLocaleString()}`,
      description: `Running ${selectedTests.size} tests`,
      tests: Array.from(selectedTests).map(testId => ({
        test_id: testId
      })),
      config: {
        execution_mode: "parallel",
        max_parallel_workers: 2,
        timeout_per_test: 30,
        retry_failed_tests: true,
        max_retries: 1,
        continue_on_failure: true
      }
    };

    try {
      const response = await fetch('http://localhost:6002/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const job = await response.json();
      setSelectedTests(new Set());
      // Refresh jobs and navigate to jobs view
      fetch('http://localhost:6002/api/jobs').then(res => res.json()).then(jobsData => {
        setJobs(jobsData);
        setCurrentView('jobs');
      });
    } catch (err) {
      alert('Failed to create job');
    }
  };

  const handleSaveAsTestSuite = () => {
    if (selectedTests.size === 0) return;
    setShowSuiteModal(true);
  };

  const handleCreateSuite = () => {
    if (!suiteFormData.name.trim()) return;
    
    const newSuite: TestSuite = {
      id: `TS_${Date.now()}`,
      name: suiteFormData.name,
      test_ids: Array.from(selectedTests),
      created_at: new Date().toISOString(),
      description: suiteFormData.description
    };
    
    setTestSuites([...testSuites, newSuite]);
    localStorage.setItem('testSuites', JSON.stringify([...testSuites, newSuite]));
    setShowSuiteModal(false);
    setSuiteFormData({ name: '', description: '' });
    setSelectedTests(new Set());
  };

  // Load saved test suites from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('testSuites');
    if (saved) {
      setTestSuites(JSON.parse(saved));
    }
  }, []);

  if (loading) {
    return <div style={{ padding: '20px' }}>Loading...</div>;
  }

  // Group tests by suite
  const testsBySuite = tests.reduce((acc, test) => {
    if (!acc[test.suite]) acc[test.suite] = [];
    acc[test.suite].push(test);
    return acc;
  }, {} as Record<string, Test[]>);

  const stats = {
    totalTests: tests.length,
    totalSuites: Object.keys(testsBySuite).length,
    byPriority: tests.reduce((acc, test) => {
      acc[test.priority] = (acc[test.priority] || 0) + 1;
      return acc;
    }, {} as Record<number, number>),
    byType: tests.reduce((acc, test) => {
      acc[test.type] = (acc[test.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>)
  };

  const priorityColors: Record<number, string> = {
    5: '#dc3545',
    4: '#fd7e14',
    3: '#ffc107',
    2: '#28a745',
    1: '#007bff'
  };

  const navStyle = {
    backgroundColor: '#343a40',
    padding: '0',
    marginBottom: '20px'
  };

  const navItemStyle = (active: boolean) => ({
    display: 'inline-block',
    padding: '15px 20px',
    color: active ? '#fff' : '#adb5bd',
    backgroundColor: active ? '#007bff' : 'transparent',
    cursor: 'pointer',
    borderRight: '1px solid #495057',
    userSelect: 'none' as const,
    transition: 'all 0.2s'
  });

  return (
    <div style={{ fontFamily: 'Arial, sans-serif' }}>
      {/* ML Server Status */}
      <div style={{
        backgroundColor: mlServerStatus?.running ? (mlServerStatus.enhanced_logging ? '#28a745' : '#ffc107') : '#dc3545',
        color: 'white',
        padding: '8px 20px',
        fontSize: '14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span style={{ marginRight: '10px' }}>
            {mlServerStatus?.running ? '🟢' : '🔴'}
          </span>
          <span>
            ML Server: {mlServerStatus?.running ? 'Running' : 'Not Running'}
            {mlServerStatus?.running && (
              <span style={{ marginLeft: '10px' }}>
                ({mlServerStatus.enhanced_logging ? '✅ Enhanced Logging' : '⚠️ Basic Logging'})
              </span>
            )}
          </span>
        </div>
        <button
          onClick={checkMlServerStatus}
          style={{
            backgroundColor: 'transparent',
            border: '1px solid white',
            color: 'white',
            padding: '4px 12px',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          Refresh Status
        </button>
      </div>

      {/* Navigation */}
      <div style={navStyle}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <button 
            style={{
              ...navItemStyle(currentView === 'dashboard'),
              border: 'none',
              font: 'inherit'
            }} 
            onClick={() => {
              console.log('Dashboard clicked');
              setCurrentView('dashboard');
            }}
          >
            Dashboard
          </button>
          <button 
            style={{
              ...navItemStyle(currentView === 'tests'),
              border: 'none',
              font: 'inherit'
            }} 
            onClick={() => {
              console.log('Test Selection clicked');
              setCurrentView('tests');
            }}
          >
            Test Selection
          </button>
          <button 
            style={{
              ...navItemStyle(currentView === 'jobs'),
              border: 'none',
              font: 'inherit'
            }} 
            onClick={() => {
              console.log('Jobs clicked');
              setCurrentView('jobs');
            }}
          >
            Jobs ({jobs.length})
          </button>
          <button 
            style={{
              ...navItemStyle(currentView === 'suites'),
              border: 'none',
              font: 'inherit'
            }} 
            onClick={() => {
              console.log('Test Suites clicked');
              setCurrentView('suites');
            }}
          >
            Test Suites ({testSuites.length})
          </button>
          <button 
            style={{
              ...navItemStyle(currentView === 'results'),
              border: 'none',
              font: 'inherit'
            }} 
            onClick={() => {
              console.log('Results clicked');
              setCurrentView('results');
            }}
          >
            Results
          </button>
        </div>
      </div>

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 20px' }}>
        {/* Dashboard View */}
        {currentView === 'dashboard' && (
          <div>
            <h1>Test Management Dashboard</h1>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', marginBottom: '30px' }}>
              <div style={{ backgroundColor: '#f8f9fa', padding: '20px', borderRadius: '8px', border: '1px solid #dee2e6' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#6c757d' }}>Total Tests</h3>
                <p style={{ fontSize: '32px', margin: 0, fontWeight: 'bold' }}>{stats.totalTests}</p>
              </div>
              
              <div style={{ backgroundColor: '#f8f9fa', padding: '20px', borderRadius: '8px', border: '1px solid #dee2e6' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#6c757d' }}>Test Suites</h3>
                <p style={{ fontSize: '32px', margin: 0, fontWeight: 'bold' }}>{stats.totalSuites}</p>
              </div>
              
              <div style={{ backgroundColor: '#f8f9fa', padding: '20px', borderRadius: '8px', border: '1px solid #dee2e6' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#6c757d' }}>Active Jobs</h3>
                <p style={{ fontSize: '32px', margin: 0, fontWeight: 'bold' }}>{jobs.filter(j => j.status === 'running').length}</p>
              </div>
              
              <div style={{ backgroundColor: '#f8f9fa', padding: '20px', borderRadius: '8px', border: '1px solid #dee2e6' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#6c757d' }}>Saved Suites</h3>
                <p style={{ fontSize: '32px', margin: 0, fontWeight: 'bold' }}>{testSuites.length}</p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              <div style={{ backgroundColor: '#f8f9fa', padding: '20px', borderRadius: '8px', border: '1px solid #dee2e6' }}>
                <h3>Tests by Priority</h3>
                {Object.entries(stats.byPriority).sort(([a], [b]) => Number(b) - Number(a)).map(([priority, count]) => (
                  <div key={priority} style={{ marginBottom: '10px' }}>
                    <span style={{
                      display: 'inline-block',
                      width: '60px',
                      padding: '2px 8px',
                      backgroundColor: priorityColors[Number(priority)],
                      color: 'white',
                      borderRadius: '12px',
                      fontSize: '12px',
                      textAlign: 'center'
                    }}>
                      P{priority}
                    </span>
                    <span style={{ marginLeft: '10px' }}>{count} tests</span>
                  </div>
                ))}
              </div>

              <div style={{ backgroundColor: '#f8f9fa', padding: '20px', borderRadius: '8px', border: '1px solid #dee2e6' }}>
                <h3>Tests by Type</h3>
                {Object.entries(stats.byType).map(([type, count]) => (
                  <div key={type} style={{ marginBottom: '10px' }}>
                    <span style={{ fontWeight: 'bold' }}>{type}:</span>
                    <span style={{ marginLeft: '10px' }}>{count} tests</span>
                  </div>
                ))}
              </div>
            </div>

            {/* System Information Panel */}
            {systemInfo && (
              <div style={{ marginTop: '30px', backgroundColor: '#f8f9fa', padding: '20px', borderRadius: '8px', border: '1px solid #dee2e6' }}>
                <h2 style={{ marginBottom: '20px' }}>System Information</h2>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                  <div>
                    <h3 style={{ fontSize: '16px', marginBottom: '10px', color: '#495057' }}>Database Connection</h3>
                    <div style={{ fontSize: '14px', lineHeight: '1.6' }}>
                      <div><strong>Host:</strong> {systemInfo.database.host}</div>
                      <div><strong>Port:</strong> {systemInfo.database.port}</div>
                      <div><strong>Database:</strong> {systemInfo.database.database}</div>
                      <div><strong>Schema:</strong> {systemInfo.database.schema}</div>
                      <div><strong>User:</strong> {systemInfo.database.user}</div>
                      <div><strong>Password:</strong> {systemInfo.database.password}</div>
                      <div>
                        <strong>Status:</strong> 
                        <span style={{ 
                          marginLeft: '5px', 
                          color: systemInfo.database.available ? '#28a745' : '#dc3545' 
                        }}>
                          {systemInfo.database.available ? '✓ Connected' : '✗ Disconnected'}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h3 style={{ fontSize: '16px', marginBottom: '10px', color: '#495057' }}>Dashboard Services</h3>
                    <div style={{ fontSize: '14px', lineHeight: '1.6' }}>
                      <div><strong>Backend API:</strong> Port {systemInfo.dashboard.backend_port}</div>
                      <div><strong>Frontend UI:</strong> Port {systemInfo.dashboard.frontend_port}</div>
                      <div><strong>API Documentation:</strong> <a href={systemInfo.dashboard.api_docs} target="_blank" rel="noopener noreferrer">{systemInfo.dashboard.api_docs}</a></div>
                    </div>
                    
                    <h3 style={{ fontSize: '16px', marginTop: '20px', marginBottom: '10px', color: '#495057' }}>ML Test Server</h3>
                    <div style={{ fontSize: '14px', lineHeight: '1.6' }}>
                      <div><strong>Base Port:</strong> {systemInfo.ml_server.base_port}</div>
                      <div><strong>Digit/Environment:</strong> {systemInfo.ml_server.digit}</div>
                      <div><strong>Test Port:</strong> {systemInfo.ml_server.test_port}</div>
                      <div style={{ color: '#6c757d', fontSize: '12px', marginTop: '5px' }}>
                        {systemInfo.ml_server.description}
                      </div>
                    </div>
                  </div>
                </div>
                
                {systemInfo.test_environments && systemInfo.test_environments.length > 0 && (
                  <div style={{ marginTop: '20px' }}>
                    <h3 style={{ fontSize: '16px', marginBottom: '10px', color: '#495057' }}>Available Test Environments</h3>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                      <thead>
                        <tr style={{ borderBottom: '2px solid #dee2e6' }}>
                          <th style={{ padding: '8px', textAlign: 'left' }}>Name</th>
                          <th style={{ padding: '8px', textAlign: 'left' }}>Digit</th>
                          <th style={{ padding: '8px', textAlign: 'left' }}>Port</th>
                          <th style={{ padding: '8px', textAlign: 'left' }}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {systemInfo.test_environments.map((env: any) => (
                          <tr key={env.digit} style={{ borderBottom: '1px solid #dee2e6' }}>
                            <td style={{ padding: '8px' }}>{env.name}</td>
                            <td style={{ padding: '8px' }}>{env.digit}</td>
                            <td style={{ padding: '8px' }}>{env.port}</td>
                            <td style={{ padding: '8px' }}>
                              <span style={{ 
                                color: env.status === 'active' ? '#28a745' : '#6c757d' 
                              }}>
                                {env.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
            
            {/* Multi-Instance Control Panel */}
            <div style={{ marginTop: '30px' }}>
              <InstanceControl />
            </div>
          </div>
        )}

        {/* Test Selection View */}
        {currentView === 'tests' && (
          <div>
            <h1>Test Selection</h1>
            <p style={{ marginBottom: '20px', color: '#6c757d' }}>
              Total: {tests.length} tests across {Object.keys(testsBySuite).length} suites
            </p>
            
            <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <label style={{ marginRight: '20px' }}>
                  <input 
                    type="checkbox" 
                    checked={selectedTests.size === tests.length && tests.length > 0}
                    onChange={handleSelectAll}
                    style={{ marginRight: '5px' }}
                  />
                  Select All ({selectedTests.size} of {tests.length} selected)
                </label>
              </div>
              <div>
                <button 
                  onClick={handleSaveAsTestSuite}
                  disabled={selectedTests.size === 0}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: selectedTests.size > 0 ? 'pointer' : 'not-allowed',
                    marginRight: '10px'
                  }}
                >
                  Save as Test Suite
                </button>
                <button 
                  onClick={handleCreateJob}
                  disabled={selectedTests.size === 0}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: selectedTests.size > 0 ? '#007bff' : '#ccc',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: selectedTests.size > 0 ? 'pointer' : 'not-allowed'
                  }}
                >
                  Create Job
                </button>
              </div>
            </div>

            <div style={{ backgroundColor: '#f8f9fa', borderRadius: '8px', overflow: 'hidden' }}>
              {Object.entries(testsBySuite).map(([suite, suiteTests]) => {
                const allSelected = suiteTests.every(t => selectedTests.has(t.id));
                const someSelected = suiteTests.some(t => selectedTests.has(t.id));
                
                return (
                  <div key={suite} style={{ marginBottom: '20px' }}>
                    <h3 style={{ 
                      backgroundColor: '#e9ecef', 
                      padding: '10px 15px', 
                      margin: 0,
                      fontSize: '16px',
                      fontWeight: 'normal',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <span>{suite} ({suiteTests.length} tests)</span>
                      <label>
                        <input 
                          type="checkbox"
                          checked={allSelected}
                          ref={input => {
                            if (input) {
                              input.indeterminate = !allSelected && someSelected;
                            }
                          }}
                          onChange={() => handleSelectSuite(suite)}
                          style={{ marginRight: '5px' }}
                        />
                        Select all in {suite}
                      </label>
                    </h3>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ backgroundColor: '#f8f9fa' }}>
                          <th style={{ padding: '10px', textAlign: 'left', width: '40px' }}></th>
                          <th style={{ padding: '10px', textAlign: 'left' }}>Test ID</th>
                          <th style={{ padding: '10px', textAlign: 'left' }}>Name</th>
                          <th style={{ padding: '10px', textAlign: 'left' }}>Type</th>
                          <th style={{ padding: '10px', textAlign: 'center' }}>Priority</th>
                          <th style={{ padding: '10px', textAlign: 'left' }}>Tags</th>
                          <th style={{ padding: '10px', textAlign: 'center' }}>Details</th>
                        </tr>
                      </thead>
                      <tbody>
                        {suiteTests.map(test => (
                          <tr key={test.id} style={{ borderBottom: '1px solid #dee2e6' }}>
                            <td style={{ padding: '10px', textAlign: 'center' }}>
                              <input 
                                type="checkbox"
                                checked={selectedTests.has(test.id)}
                                onChange={() => handleSelectTest(test.id)}
                              />
                            </td>
                            <td style={{ padding: '10px', fontFamily: 'monospace', fontSize: '13px' }}>{test.id}</td>
                            <td style={{ padding: '10px' }}>{test.name}</td>
                            <td style={{ padding: '10px' }}>{test.type}</td>
                            <td style={{ padding: '10px', textAlign: 'center' }}>
                              <span style={{
                                display: 'inline-block',
                                padding: '2px 8px',
                                backgroundColor: priorityColors[test.priority],
                                color: 'white',
                                borderRadius: '12px',
                                fontSize: '12px'
                              }}>
                                P{test.priority}
                              </span>
                            </td>
                            <td style={{ padding: '10px' }}>
                              {test.tags.slice(0, 3).map((tag, idx) => (
                                <span key={idx} style={{
                                  display: 'inline-block',
                                  padding: '2px 6px',
                                  backgroundColor: '#e9ecef',
                                  borderRadius: '3px',
                                  fontSize: '11px',
                                  marginRight: '4px'
                                }}>
                                  {tag}
                                </span>
                              ))}
                              {test.tags.length > 3 && (
                                <span style={{ fontSize: '11px', color: '#6c757d' }}>
                                  +{test.tags.length - 3} more
                                </span>
                              )}
                            </td>
                            <td style={{ padding: '10px', textAlign: 'center' }}>
                              <button
                                onClick={() => fetchTestDetails(test.id)}
                                style={{
                                  padding: '4px 8px',
                                  backgroundColor: '#007bff',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  fontSize: '12px',
                                  cursor: 'pointer'
                                }}
                              >
                                View
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Jobs View */}
        {currentView === 'jobs' && (
          <div>
            <h1>Jobs</h1>
            <p style={{ marginBottom: '20px', color: '#6c757d' }}>
              Manage and monitor test execution jobs
            </p>
            
            {jobs.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                padding: '60px 20px',
                backgroundColor: '#f8f9fa',
                borderRadius: '8px',
                border: '1px solid #dee2e6'
              }}>
                <h3 style={{ color: '#6c757d', marginBottom: '10px' }}>No Jobs Yet</h3>
                <p style={{ marginBottom: '20px' }}>Create your first job by selecting tests and clicking "Create Job".</p>
                <button
                  onClick={() => setCurrentView('tests')}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Go to Test Selection
                </button>
              </div>
            ) : (
              <div>
                <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: '#fff' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                      <th style={{ padding: '12px', textAlign: 'left' }}>Job Name</th>
                      <th style={{ padding: '12px', textAlign: 'left' }}>Status</th>
                      <th style={{ padding: '12px', textAlign: 'center' }}>Tests</th>
                      <th style={{ padding: '12px', textAlign: 'center' }}>Progress</th>
                      <th style={{ padding: '12px', textAlign: 'left' }}>Created</th>
                      <th style={{ padding: '12px', textAlign: 'center' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.map(job => {
                      const statusColors: Record<string, string> = {
                        created: '#6c757d',
                        queued: '#ffc107',
                        running: '#007bff',
                        completed: '#28a745',
                        failed: '#dc3545',
                        cancelled: '#6c757d'
                      };
                      
                      const progress = job.total_tests ? 
                        Math.round((job.completed_tests || 0) / job.total_tests * 100) : 0;
                      
                      return (
                        <tr key={job.id} style={{ borderBottom: '1px solid #dee2e6' }}>
                          <td style={{ padding: '12px' }}>
                            <div>
                              <strong>{job.name}</strong>
                              {job.description && (
                                <div style={{ fontSize: '12px', color: '#6c757d' }}>{job.description}</div>
                              )}
                            </div>
                          </td>
                          <td style={{ padding: '12px' }}>
                            <span style={{
                              display: 'inline-block',
                              padding: '4px 8px',
                              backgroundColor: statusColors[job.status] || '#6c757d',
                              color: 'white',
                              borderRadius: '4px',
                              fontSize: '12px',
                              textTransform: 'uppercase'
                            }}>
                              {job.status}
                            </span>
                          </td>
                          <td style={{ padding: '12px', textAlign: 'center' }}>
                            {job.tests.length}
                          </td>
                          <td style={{ padding: '12px' }}>
                            {job.status === 'running' || job.status === 'completed' ? (
                              <div>
                                <div style={{ 
                                  width: '100px', 
                                  height: '20px', 
                                  backgroundColor: '#e9ecef',
                                  borderRadius: '4px',
                                  overflow: 'hidden',
                                  margin: '0 auto'
                                }}>
                                  <div style={{
                                    width: `${progress}%`,
                                    height: '100%',
                                    backgroundColor: (job.failed_tests || 0) > 0 ? '#fd7e14' : '#28a745',
                                    transition: 'width 0.3s'
                                  }} />
                                </div>
                                <div style={{ fontSize: '11px', textAlign: 'center', marginTop: '2px' }}>
                                  {job.completed_tests || 0}/{job.total_tests || job.tests.length}
                                </div>
                              </div>
                            ) : (
                              <div style={{ textAlign: 'center', color: '#6c757d' }}>-</div>
                            )}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'center' }}>
                            {job.status === 'completed' && job.total_tests ? (
                              <div>
                                <span style={{
                                  fontSize: '14px',
                                  fontWeight: 'bold',
                                  color: (job.failed_tests || 0) === 0 ? '#28a745' : (job.failed_tests || 0) / job.total_tests > 0.5 ? '#dc3545' : '#fd7e14'
                                }}>
                                  {Math.round(((job.total_tests - (job.failed_tests || 0)) / job.total_tests) * 100)}%
                                </span>
                                <div style={{ fontSize: '11px', color: '#6c757d' }}>
                                  {job.total_tests - (job.failed_tests || 0)}/{job.total_tests} passed
                                </div>
                              </div>
                            ) : (
                              '-'
                            )}
                          </td>
                          <td style={{ padding: '12px', fontSize: '13px' }}>
                            {new Date(job.created_at).toLocaleString()}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'center' }}>
                            <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                              <button
                                onClick={() => fetchJobDetails(job.id)}
                                style={{
                                  padding: '4px 12px',
                                  backgroundColor: '#007bff',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  fontSize: '12px',
                                  cursor: 'pointer'
                                }}
                              >
                                Details
                              </button>
                              {job.status === 'created' && (
                                <button
                                  onClick={() => executeJob(job.id)}
                                  style={{
                                    padding: '4px 12px',
                                    backgroundColor: '#28a745',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    fontSize: '12px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  Run
                                </button>
                              )}
                              {job.status === 'running' && (
                                <button
                                  onClick={() => stopJob(job.id)}
                                  style={{
                                    padding: '4px 12px',
                                    backgroundColor: '#dc3545',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    fontSize: '12px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  Stop
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Test Suites View */}
        {currentView === 'suites' && (
          <div>
            <h1>Test Suites</h1>
            <p style={{ marginBottom: '20px', color: '#6c757d' }}>
              Manage your saved test collections
            </p>
            
            {testSuites.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                padding: '60px 20px',
                backgroundColor: '#f8f9fa',
                borderRadius: '8px',
                border: '1px solid #dee2e6'
              }}>
                <h3 style={{ color: '#6c757d', marginBottom: '10px' }}>No Test Suites Yet</h3>
                <p style={{ marginBottom: '20px' }}>Create your first test suite by selecting tests and saving them as a collection.</p>
                <button
                  onClick={() => setCurrentView('tests')}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Go to Test Selection
                </button>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '20px' }}>
                {testSuites.map(suite => {
                  const suiteTests = tests.filter(t => suite.test_ids.includes(t.id));
                  const suiteSummary = suiteTests.reduce((acc, test) => {
                    acc[test.suite] = (acc[test.suite] || 0) + 1;
                    return acc;
                  }, {} as Record<string, number>);
                  
                  return (
                    <div key={suite.id} style={{ 
                      backgroundColor: '#fff', 
                      padding: '20px', 
                      borderRadius: '8px',
                      border: '1px solid #dee2e6',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
                    }}>
                      <h3 style={{ margin: '0 0 10px 0', fontSize: '18px' }}>{suite.name}</h3>
                      {suite.description && (
                        <p style={{ color: '#6c757d', fontSize: '14px', marginBottom: '15px' }}>
                          {suite.description}
                        </p>
                      )}
                      
                      <div style={{ marginBottom: '15px' }}>
                        <div style={{ fontSize: '14px', color: '#495057', marginBottom: '5px' }}>
                          <strong>{suite.test_ids.length}</strong> tests in <strong>{Object.keys(suiteSummary).length}</strong> categories
                        </div>
                        <div style={{ fontSize: '12px', color: '#6c757d' }}>
                          Created: {new Date(suite.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      
                      {Object.keys(suiteSummary).length > 0 && (
                        <div style={{ 
                          backgroundColor: '#f8f9fa', 
                          padding: '10px', 
                          borderRadius: '4px',
                          marginBottom: '15px',
                          fontSize: '12px'
                        }}>
                          {Object.entries(suiteSummary).slice(0, 3).map(([cat, count]) => (
                            <div key={cat} style={{ marginBottom: '2px' }}>
                              • {cat}: {count} tests
                            </div>
                          ))}
                          {Object.keys(suiteSummary).length > 3 && (
                            <div style={{ color: '#6c757d', fontStyle: 'italic' }}>
                              +{Object.keys(suiteSummary).length - 3} more categories
                            </div>
                          )}
                        </div>
                      )}
                      
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <button
                          onClick={() => {
                            setSelectedTests(new Set(suite.test_ids));
                            setCurrentView('tests');
                          }}
                          style={{
                            flex: 1,
                            padding: '8px 16px',
                            backgroundColor: '#007bff',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '14px'
                          }}
                        >
                          Load Tests
                        </button>
                        <button
                          onClick={() => {
                            if (window.confirm(`Delete test suite "${suite.name}"?`)) {
                              const newSuites = testSuites.filter(s => s.id !== suite.id);
                              setTestSuites(newSuites);
                              localStorage.setItem('testSuites', JSON.stringify(newSuites));
                            }
                          }}
                          style={{
                            padding: '8px 16px',
                            backgroundColor: '#dc3545',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '14px'
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Results View */}
        {currentView === 'results' && (
          <div>
            <h1>Test Results</h1>
            <p>Results view coming soon...</p>
          </div>
        )}

        {/* Test Detail Modal */}
        {selectedTest && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}>
            <div style={{
              backgroundColor: 'white',
              padding: '30px',
              borderRadius: '8px',
              maxWidth: '800px',
              width: '90%',
              maxHeight: '90vh',
              overflow: 'auto'
            }}>
              <h2>{selectedTest.name}</h2>
              
              <div style={{ marginBottom: '20px' }}>
                <h3>Basic Information</h3>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <tbody>
                    <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                      <td style={{ padding: '8px', fontWeight: 'bold', width: '150px' }}>Test ID</td>
                      <td style={{ padding: '8px', fontFamily: 'monospace' }}>{selectedTest.id}</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                      <td style={{ padding: '8px', fontWeight: 'bold' }}>Suite</td>
                      <td style={{ padding: '8px' }}>{selectedTest.suite}</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                      <td style={{ padding: '8px', fontWeight: 'bold' }}>Type</td>
                      <td style={{ padding: '8px' }}>{selectedTest.type === 'single' ? 'Single Turn' : 'Multi Turn'}</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                      <td style={{ padding: '8px', fontWeight: 'bold' }}>Priority</td>
                      <td style={{ padding: '8px' }}>
                        <span style={{
                          padding: '2px 8px',
                          backgroundColor: priorityColors[selectedTest.priority],
                          color: 'white',
                          borderRadius: '12px',
                          fontSize: '12px'
                        }}>
                          P{selectedTest.priority}
                        </span>
                        {' '}
                        {selectedTest.priority === 5 ? '(Critical)' : 
                         selectedTest.priority === 4 ? '(High)' :
                         selectedTest.priority === 3 ? '(Medium)' :
                         selectedTest.priority === 2 ? '(Low)' : '(Minimal)'}
                      </td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                      <td style={{ padding: '8px', fontWeight: 'bold' }}>Tags</td>
                      <td style={{ padding: '8px' }}>
                        {selectedTest.tags.map((tag, idx) => (
                          <span key={idx} style={{
                            display: 'inline-block',
                            padding: '2px 6px',
                            backgroundColor: '#e9ecef',
                            borderRadius: '3px',
                            fontSize: '11px',
                            marginRight: '4px',
                            marginBottom: '4px'
                          }}>
                            {tag}
                          </span>
                        ))}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {!showFullJson ? (
                <>
                  {selectedTest.config && (
                    <div style={{ marginBottom: '20px' }}>
                      <h3>Configuration</h3>
                      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <tbody>
                          <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                            <td style={{ padding: '8px', fontWeight: 'bold', width: '150px' }}>Timeout</td>
                            <td style={{ padding: '8px' }}>{selectedTest.config.timeout || 30} seconds</td>
                          </tr>
                          <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                            <td style={{ padding: '8px', fontWeight: 'bold' }}>Retries</td>
                            <td style={{ padding: '8px' }}>{selectedTest.config.retries || 0}</td>
                          </tr>
                          <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                            <td style={{ padding: '8px', fontWeight: 'bold' }}>Parallel Safe</td>
                            <td style={{ padding: '8px' }}>{selectedTest.config.parallel_safe ? 'Yes' : 'No'}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  )}

                  {selectedTest.execution && (
                    <div style={{ marginBottom: '20px' }}>
                      <h3>Execution Details</h3>
                      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <tbody>
                          <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                            <td style={{ padding: '8px', fontWeight: 'bold', width: '150px' }}>Endpoint</td>
                            <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: '13px' }}>{selectedTest.execution.endpoint}</td>
                          </tr>
                          <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                            <td style={{ padding: '8px', fontWeight: 'bold' }}>Method</td>
                            <td style={{ padding: '8px' }}>{selectedTest.execution.method}</td>
                          </tr>
                          {selectedTest.execution.payload?.input && (
                            <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                              <td style={{ padding: '8px', fontWeight: 'bold' }}>Input Query</td>
                              <td style={{ padding: '8px', backgroundColor: '#f8f9fa', fontStyle: 'italic' }}>
                                "{selectedTest.execution.payload.input}"
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {selectedTest.expectations && (
                    <div style={{ marginBottom: '20px' }}>
                      <h3>Expected Results</h3>
                      {selectedTest.expectations.response && (
                        <>
                          <h4 style={{ fontSize: '14px', marginTop: '10px' }}>Response Expectations</h4>
                          <ul style={{ fontSize: '14px' }}>
                            <li>Status Code: {selectedTest.expectations.response.status_code || 200}</li>
                            {selectedTest.expectations.response.output_contains && selectedTest.expectations.response.output_contains.length > 0 && (
                              <li>Output must contain: {selectedTest.expectations.response.output_contains.join(', ')}</li>
                            )}
                            {selectedTest.expectations.response.min_length && (
                              <li>Minimum response length: {selectedTest.expectations.response.min_length} characters</li>
                            )}
                          </ul>
                        </>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div style={{ marginBottom: '20px' }}>
                  <h3>Full Test Definition (JSON)</h3>
                  <pre style={{
                    backgroundColor: '#f8f9fa',
                    padding: '15px',
                    borderRadius: '4px',
                    overflow: 'auto',
                    fontSize: '12px',
                    maxHeight: '400px'
                  }}>
                    {JSON.stringify(selectedTest, null, 2)}
                  </pre>
                </div>
              )}

              <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                <button
                  onClick={() => setShowFullJson(!showFullJson)}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  {showFullJson ? 'Show Formatted View' : 'Show Full JSON'}
                </button>
                <button
                  onClick={() => {
                    setSelectedTest(null);
                    setShowFullJson(false);
                  }}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Test Suite Creation Modal */}
        {showSuiteModal && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}>
            <div style={{
              backgroundColor: 'white',
              padding: '30px',
              borderRadius: '8px',
              maxWidth: '500px',
              width: '90%'
            }}>
              <h2>Create Test Suite</h2>
              <p style={{ marginBottom: '20px', color: '#6c757d' }}>
                Save {selectedTests.size} selected tests as a reusable test suite
              </p>
              
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                  Suite Name *
                </label>
                <input
                  type="text"
                  value={suiteFormData.name}
                  onChange={(e) => setSuiteFormData({ ...suiteFormData, name: e.target.value })}
                  placeholder="e.g., Critical Appointment Tests"
                  style={{
                    width: '100%',
                    padding: '10px',
                    border: '1px solid #ced4da',
                    borderRadius: '4px',
                    fontSize: '14px'
                  }}
                />
              </div>
              
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                  Description
                </label>
                <textarea
                  value={suiteFormData.description}
                  onChange={(e) => setSuiteFormData({ ...suiteFormData, description: e.target.value })}
                  placeholder="Describe the purpose of this test suite..."
                  rows={4}
                  style={{
                    width: '100%',
                    padding: '10px',
                    border: '1px solid #ced4da',
                    borderRadius: '4px',
                    fontSize: '14px',
                    resize: 'vertical'
                  }}
                />
              </div>
              
              <div style={{ marginBottom: '20px', backgroundColor: '#f8f9fa', padding: '15px', borderRadius: '4px' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '14px' }}>Selected Tests Summary</h4>
                <div style={{ fontSize: '13px' }}>
                  {(() => {
                    const selectedTestObjs = tests.filter(t => selectedTests.has(t.id));
                    const suiteBreakdown = selectedTestObjs.reduce((acc, test) => {
                      acc[test.suite] = (acc[test.suite] || 0) + 1;
                      return acc;
                    }, {} as Record<string, number>);
                    
                    return Object.entries(suiteBreakdown).map(([suite, count]) => (
                      <div key={suite} style={{ marginBottom: '4px' }}>
                        • {suite}: {count} tests
                      </div>
                    ));
                  })()}
                </div>
              </div>
              
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button
                  onClick={() => {
                    setShowSuiteModal(false);
                    setSuiteFormData({ name: '', description: '' });
                  }}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateSuite}
                  disabled={!suiteFormData.name.trim()}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: suiteFormData.name.trim() ? '#28a745' : '#ccc',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: suiteFormData.name.trim() ? 'pointer' : 'not-allowed'
                  }}
                >
                  Create Suite
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Job Detail Modal */}
        {selectedJob && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}>
            <div style={{
              backgroundColor: 'white',
              padding: '30px',
              borderRadius: '8px',
              maxWidth: '900px',
              width: '90%',
              maxHeight: '90vh',
              overflow: 'auto'
            }}>
              <h2>Job Details: {selectedJob.name}</h2>
              
              <div style={{ marginBottom: '20px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <tbody>
                    <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                      <td style={{ padding: '8px', fontWeight: 'bold', width: '150px' }}>Status</td>
                      <td style={{ padding: '8px' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '4px 8px',
                          backgroundColor: {
                            created: '#6c757d',
                            queued: '#ffc107',
                            running: '#007bff',
                            completed: '#28a745',
                            failed: '#dc3545',
                            cancelled: '#6c757d'
                          }[selectedJob.status] || '#6c757d',
                          color: 'white',
                          borderRadius: '4px',
                          fontSize: '12px',
                          textTransform: 'uppercase'
                        }}>
                          {selectedJob.status}
                        </span>
                      </td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                      <td style={{ padding: '8px', fontWeight: 'bold' }}>Priority</td>
                      <td style={{ padding: '8px' }}>{selectedJob.priority}</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                      <td style={{ padding: '8px', fontWeight: 'bold' }}>Created</td>
                      <td style={{ padding: '8px' }}>{new Date(selectedJob.created_at).toLocaleString()}</td>
                    </tr>
                    {selectedJob.started_at && (
                      <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                        <td style={{ padding: '8px', fontWeight: 'bold' }}>Started</td>
                        <td style={{ padding: '8px' }}>{new Date(selectedJob.started_at).toLocaleString()}</td>
                      </tr>
                    )}
                    {selectedJob.completed_at && (
                      <tr style={{ borderBottom: '1px solid #dee2e6' }}>
                        <td style={{ padding: '8px', fontWeight: 'bold' }}>Completed</td>
                        <td style={{ padding: '8px' }}>{new Date(selectedJob.completed_at).toLocaleString()}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              <h3>Execution Configuration</h3>
              <div style={{ marginBottom: '20px', backgroundColor: '#f8f9fa', padding: '15px', borderRadius: '4px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '14px' }}>
                  <div>Mode: {selectedJob.config.execution_mode}</div>
                  <div>Workers: {selectedJob.config.max_parallel_workers}</div>
                  <div>Timeout: {selectedJob.config.timeout_per_test}s per test</div>
                  <div>Retries: {selectedJob.config.max_retries}</div>
                </div>
              </div>

              <h3>Test Execution Status ({selectedJob.tests.length} tests)</h3>
              <div style={{ maxHeight: '300px', overflow: 'auto', border: '1px solid #dee2e6', borderRadius: '4px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead style={{ position: 'sticky', top: 0, backgroundColor: '#f8f9fa' }}>
                    <tr>
                      <th style={{ padding: '10px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Test ID</th>
                      <th style={{ padding: '10px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Suite</th>
                      <th style={{ padding: '10px', textAlign: 'center', borderBottom: '2px solid #dee2e6' }}>Status</th>
                      <th style={{ padding: '10px', textAlign: 'center', borderBottom: '2px solid #dee2e6' }}>Duration</th>
                      <th style={{ padding: '10px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Result</th>
                      <th style={{ padding: '10px', textAlign: 'center', borderBottom: '2px solid #dee2e6' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedJob.tests.map((testRef, idx) => {
                      const result = jobResults.results?.[testRef.test_id];
                      const test = tests.find(t => t.id === testRef.test_id);
                      
                      return (
                        <tr key={idx} style={{ borderBottom: '1px solid #dee2e6' }}>
                          <td style={{ padding: '10px', fontFamily: 'monospace', fontSize: '13px' }}>
                            {testRef.test_id}
                          </td>
                          <td style={{ padding: '10px', fontSize: '13px' }}>
                            {test?.suite || testRef.suite || '-'}
                          </td>
                          <td style={{ padding: '10px', textAlign: 'center' }}>
                            {result ? (
                              <span style={{
                                display: 'inline-block',
                                padding: '2px 8px',
                                backgroundColor: result.success ? '#28a745' : '#dc3545',
                                color: 'white',
                                borderRadius: '4px',
                                fontSize: '11px'
                              }}>
                                {result.status}
                              </span>
                            ) : (
                              <span style={{ color: '#6c757d', fontSize: '11px' }}>Pending</span>
                            )}
                          </td>
                          <td style={{ padding: '10px', textAlign: 'center', fontSize: '13px' }}>
                            {result ? `${result.duration}s` : '-'}
                          </td>
                          <td style={{ padding: '10px', fontSize: '12px' }}>
                            {result?.error ? (
                              <span style={{ color: '#dc3545' }}>{result.error}</span>
                            ) : result?.success ? (
                              <span style={{ color: '#28a745' }}>Passed</span>
                            ) : (
                              '-'
                            )}
                          </td>
                          <td style={{ padding: '10px', textAlign: 'center' }}>
                            {result && (
                              <button
                                onClick={async () => {
                                  setSelectedTestResult(result);
                                  // Fetch test logs
                                  try {
                                    const logsResponse = await fetch(`http://localhost:6002/api/results/${selectedJob.id}/${jobResults.run_id}/${result.test_id}/logs`);
                                    if (logsResponse.ok) {
                                      const logs = await logsResponse.json();
                                      setTestLogs(logs);
                                    }
                                  } catch (err) {
                                    console.error('Failed to fetch test logs:', err);
                                  }
                                }}
                                style={{
                                  padding: '4px 12px',
                                  backgroundColor: '#17a2b8',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  fontSize: '12px',
                                  cursor: 'pointer'
                                }}
                              >
                                Details
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div style={{ display: 'flex', gap: '10px', marginTop: '20px', justifyContent: 'flex-end' }}>
                {selectedJob.status === 'created' && (
                  <button
                    onClick={() => {
                      executeJob(selectedJob.id);
                      setSelectedJob(null);
                    }}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: '#28a745',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Run Job
                  </button>
                )}
                {selectedJob.status === 'running' && (
                  <button
                    onClick={() => {
                      stopJob(selectedJob.id);
                      setSelectedJob(null);
                    }}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: '#dc3545',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Stop Job
                  </button>
                )}
                <button
                  onClick={() => {
                    setSelectedJob(null);
                    setJobResults({});
                  }}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Test Result Details Modal */}
        {selectedTestResult && (
          <div 
            onClick={(e) => {
              // Close modal when clicking backdrop
              if (e.target === e.currentTarget) {
                setSelectedTestResult(null);
                setTestLogs(null);
              }
            }}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
              cursor: 'pointer'
            }}>
            <div 
              onClick={(e) => e.stopPropagation()}
              style={{
              backgroundColor: 'white',
              borderRadius: '8px',
              padding: '30px',
              maxWidth: '800px',
              width: '90%',
              maxHeight: '80vh',
              overflow: 'auto',
              boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
              cursor: 'default'
            }}>
              <h2 style={{ marginBottom: '20px' }}>Test Result Details</h2>
              
              {/* Test Definition */}
              <div style={{ marginBottom: '20px' }}>
                <h3 style={{ fontSize: '18px', marginBottom: '10px' }}>Test Definition</h3>
                <button
                  onClick={async () => {
                    try {
                      const response = await fetch(`http://localhost:6002/api/tests/${selectedTestResult.test_id}`);
                      const testData = await response.json();
                      setSelectedTest(testData);
                    } catch (err) {
                      console.error('Failed to fetch test details:', err);
                    }
                  }}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    fontSize: '12px',
                    cursor: 'pointer',
                    marginBottom: '10px'
                  }}
                >
                  View Test Definition
                </button>
                {selectedTest && selectedTest.id === selectedTestResult.test_id && (
                  <div style={{
                    backgroundColor: '#f8f9fa',
                    padding: '15px',
                    borderRadius: '4px',
                    marginBottom: '15px'
                  }}>
                    <div style={{ marginBottom: '10px' }}>
                      <strong>Test Type:</strong> {selectedTest.type}
                    </div>
                    {selectedTest.config?.description && (
                      <div style={{ marginBottom: '10px' }}>
                        <strong>Description:</strong> {selectedTest.config.description}
                      </div>
                    )}
                    <div style={{ marginBottom: '10px' }}>
                      <strong>Priority:</strong> {selectedTest.priority}
                    </div>
                    <div style={{ marginBottom: '10px' }}>
                      <strong>Tags:</strong> {selectedTest.tags?.join(', ') || 'None'}
                    </div>
                    {selectedTest.execution?.payload && (
                      <div>
                        <strong>Test Payload:</strong>
                        <pre style={{
                          backgroundColor: 'white',
                          padding: '10px',
                          borderRadius: '4px',
                          overflow: 'auto',
                          maxHeight: '150px',
                          fontSize: '11px',
                          fontFamily: 'monospace',
                          marginTop: '5px'
                        }}>
                          {JSON.stringify(selectedTest.execution.payload, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {/* General Information */}
              <div style={{ marginBottom: '20px' }}>
                <h3 style={{ fontSize: '18px', marginBottom: '10px' }}>Execution Results</h3>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <tbody>
                    <tr>
                      <td style={{ padding: '8px', fontWeight: 'bold', width: '150px' }}>Test ID:</td>
                      <td style={{ padding: '8px', fontFamily: 'monospace' }}>{selectedTestResult.test_id}</td>
                    </tr>
                    <tr style={{ backgroundColor: '#f8f9fa' }}>
                      <td style={{ padding: '8px', fontWeight: 'bold' }}>Suite:</td>
                      <td style={{ padding: '8px' }}>{selectedTestResult.suite}</td>
                    </tr>
                    <tr>
                      <td style={{ padding: '8px', fontWeight: 'bold' }}>Name:</td>
                      <td style={{ padding: '8px' }}>{selectedTestResult.name}</td>
                    </tr>
                    <tr style={{ backgroundColor: '#f8f9fa' }}>
                      <td style={{ padding: '8px', fontWeight: 'bold' }}>Status:</td>
                      <td style={{ padding: '8px' }}>
                        <span style={{
                          padding: '2px 8px',
                          backgroundColor: selectedTestResult.success ? '#28a745' : '#dc3545',
                          color: 'white',
                          borderRadius: '4px',
                          fontSize: '12px'
                        }}>
                          {selectedTestResult.success ? 'PASSED' : 'FAILED'}
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td style={{ padding: '8px', fontWeight: 'bold' }}>Duration:</td>
                      <td style={{ padding: '8px' }}>{selectedTestResult.duration}s</td>
                    </tr>
                    <tr style={{ backgroundColor: '#f8f9fa' }}>
                      <td style={{ padding: '8px', fontWeight: 'bold' }}>Started At:</td>
                      <td style={{ padding: '8px' }}>{new Date(selectedTestResult.started_at).toLocaleString()}</td>
                    </tr>
                    <tr>
                      <td style={{ padding: '8px', fontWeight: 'bold' }}>Completed At:</td>
                      <td style={{ padding: '8px' }}>{new Date(selectedTestResult.completed_at).toLocaleString()}</td>
                    </tr>
                    {selectedTestResult.error && (
                      <tr style={{ backgroundColor: '#f8f9fa' }}>
                        <td style={{ padding: '8px', fontWeight: 'bold' }}>Error:</td>
                        <td style={{ padding: '8px', color: '#dc3545' }}>{selectedTestResult.error}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Test Logs */}
              {testLogs && (
                <div style={{ marginBottom: '20px' }}>
                  <h3 style={{ fontSize: '18px', marginBottom: '10px' }}>Execution Logs</h3>
                  
                  {/* ML Server Logs (Agent Thinking) */}
                  {(testLogs.ml_server_logs || testLogs.server_logs) && (
                    <div style={{ marginBottom: '15px' }}>
                      <h4 style={{ fontSize: '16px', marginBottom: '5px', color: '#28a745' }}>
                        🤖 ML Server Logs (Agent Thinking Process)
                      </h4>
                      <pre style={{
                        backgroundColor: '#f8f9fa',
                        padding: '10px',
                        borderRadius: '4px',
                        overflow: 'auto',
                        maxHeight: '400px',
                        fontSize: '12px',
                        fontFamily: 'monospace',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        border: '1px solid #dee2e6'
                      }}>
                        {(() => {
                          try {
                            // First try to use ml_server_logs if available
                            if (testLogs.ml_server_logs) {
                              if (Array.isArray(testLogs.ml_server_logs)) {
                                return testLogs.ml_server_logs.join('\n');
                              } else {
                                return testLogs.ml_server_logs;
                              }
                            }
                            
                            // Fallback to parsing server_logs
                            const logsData = typeof testLogs.server_logs === 'string' 
                              ? JSON.parse(testLogs.server_logs) 
                              : testLogs.server_logs;
                            
                            // Extract ML logs from server_logs
                            if (logsData.ml_server_logs && Array.isArray(logsData.ml_server_logs)) {
                              return logsData.ml_server_logs.join('\n');
                            } else if (logsData.logs && Array.isArray(logsData.logs)) {
                              return logsData.logs.join('\n');
                            } else if (Array.isArray(logsData)) {
                              return logsData.join('\n');
                            } else {
                              // If it's not an array, stringify it nicely
                              return JSON.stringify(logsData, null, 2);
                            }
                          } catch (e) {
                            // If parsing fails, return as-is
                            return testLogs.server_logs || 'No ML server logs available';
                          }
                        })()}
                      </pre>
                    </div>
                  )}

                  {/* Backend API Server Logs (if needed) */}
                  {testLogs.backend_logs && testLogs.backend_logs.length > 0 && (
                    <div style={{ marginBottom: '15px' }}>
                      <h4 style={{ fontSize: '16px', marginBottom: '5px' }}>Backend API Server Logs</h4>
                      <pre style={{
                        backgroundColor: '#f8f9fa',
                        padding: '10px',
                        borderRadius: '4px',
                        overflow: 'auto',
                        maxHeight: '200px',
                        fontSize: '12px',
                        fontFamily: 'monospace',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                      }}>
                        {testLogs.backend_logs.join('\n')}
                      </pre>
                    </div>
                  )}

                  {/* Execution Logs */}
                  {testLogs.execution_logs && testLogs.execution_logs.length > 0 && (
                    <div style={{ marginBottom: '15px' }}>
                      <h4 style={{ fontSize: '16px', marginBottom: '5px' }}>Execution Logs</h4>
                      <div style={{
                        backgroundColor: '#f8f9fa',
                        padding: '10px',
                        borderRadius: '4px',
                        maxHeight: '200px',
                        overflow: 'auto'
                      }}>
                        {testLogs.execution_logs.map((log: any, idx: number) => (
                          <div key={idx} style={{ marginBottom: '5px', fontSize: '12px' }}>
                            <span style={{ color: '#6c757d' }}>{new Date(log.timestamp).toLocaleTimeString()}</span>
                            <span style={{
                              marginLeft: '10px',
                              color: log.level === 'ERROR' ? '#dc3545' : log.level === 'WARNING' ? '#ffc107' : '#212529'
                            }}>
                              [{log.level}] {log.message}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Request/Response Details */}
                  {testLogs.request && (
                    <div style={{ marginBottom: '15px' }}>
                      <h4 style={{ fontSize: '16px', marginBottom: '5px' }}>Request Details</h4>
                      <pre style={{
                        backgroundColor: '#f8f9fa',
                        padding: '10px',
                        borderRadius: '4px',
                        overflow: 'auto',
                        maxHeight: '300px',
                        fontSize: '12px',
                        fontFamily: 'monospace',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                      }}>
                        {(() => {
                          try {
                            // If request is a string, try to parse it
                            const requestData = typeof testLogs.request === 'string' 
                              ? JSON.parse(testLogs.request) 
                              : testLogs.request;
                            return JSON.stringify(requestData, null, 2);
                          } catch (e) {
                            // If parsing fails, return as-is
                            return testLogs.request;
                          }
                        })()}
                      </pre>
                    </div>
                  )}

                  {testLogs.response && (
                    <div style={{ marginBottom: '15px' }}>
                      <h4 style={{ fontSize: '16px', marginBottom: '5px' }}>Response Details</h4>
                      <pre style={{
                        backgroundColor: '#f8f9fa',
                        padding: '10px',
                        borderRadius: '4px',
                        overflow: 'auto',
                        maxHeight: '300px',
                        fontSize: '12px',
                        fontFamily: 'monospace',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                      }}>
                        {(() => {
                          try {
                            // If response is a string, try to parse it
                            const responseData = typeof testLogs.response === 'string' 
                              ? JSON.parse(testLogs.response) 
                              : testLogs.response;
                            return JSON.stringify(responseData, null, 2);
                          } catch (e) {
                            // If parsing fails, return as-is
                            return testLogs.response;
                          }
                        })()}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '20px' }}>
                <button
                  onClick={() => {
                    setSelectedTestResult(null);
                    setTestLogs(null);
                  }}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;