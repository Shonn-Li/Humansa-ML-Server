import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';

const InstanceControl = () => {
  const [instances, setInstances] = useState([]);
  const [status, setStatus] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Fetch instance status
  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/instances/status`);
      const data = await response.json();
      setStatus(data);
      setInstances(data.instances || []);
    } catch (err) {
      console.error('Failed to fetch instance status:', err);
    }
  };

  // Fetch settings
  const fetchSettings = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/settings/`);
      if (!response.ok) {
        if (response.status === 404) {
          // Settings endpoint not available, set default values
          console.warn('Settings endpoint not available, using defaults');
          setSettings({
            multi_instance: {
              enabled: true,
              default_instances: 4,
              auto_start: true,
              max_workers_per_job: 4
            }
          });
          return;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setSettings(data);
    } catch (err) {
      console.error('Failed to fetch settings:', err);
      // Set fallback settings so the component doesn't break
      setSettings({
        multi_instance: {
          enabled: true,
          default_instances: 4,
          auto_start: true,
          max_workers_per_job: 4
        }
      });
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchSettings();
    // Refresh every 5 seconds
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Initialize instances
  const handleInitialize = async (numInstances) => {
    setLoading(true);
    setError(null);
    try {
      // If instances exist but are stopped, shutdown first then reinitialize
      if (status?.total_instances > 0) {
        const shutdownResponse = await fetch(`${API_BASE_URL}/instances/shutdown`, {
          method: 'POST'
        });
        if (!shutdownResponse.ok) {
          console.warn('Failed to shutdown existing instances, continuing anyway');
        }
        // Wait a bit for shutdown to complete
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
      
      const response = await fetch(`${API_BASE_URL}/instances/initialize?num_instances=${numInstances}`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error('Failed to initialize instances');
      setSuccessMessage(`Successfully initialized ${numInstances} instances`);
      await fetchStatus();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Shutdown all instances
  const handleShutdown = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/instances/shutdown`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error('Failed to shutdown instances');
      setSuccessMessage('All instances shut down');
      await fetchStatus();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Update settings
  const handleSettingsUpdate = async (updates) => {
    try {
      const response = await fetch(`${API_BASE_URL}/settings/multi-instance`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      if (!response.ok) throw new Error('Failed to update settings');
      await fetchSettings();
      setSuccessMessage('Settings updated successfully');
    } catch (err) {
      setError(err.message);
    }
  };

  // Apply settings (start/stop instances to match configuration)
  const handleApplySettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/settings/multi-instance/apply`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error('Failed to apply settings');
      const result = await response.json();
      setSuccessMessage(result.actions?.join(', ') || 'Settings applied');
      await fetchStatus();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'ready': return '#4caf50';
      case 'busy': return '#ff9800';
      case 'error': return '#f44336';
      case 'starting': return '#2196f3';
      default: return '#757575';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'ready': return '✅';
      case 'busy': return '🔧';
      case 'error': return '❌';
      case 'starting': return '🔄';
      default: return '⭕';
    }
  };

  if (!settings || !settings.multi_instance) return <div style={styles.loading}>Loading...</div>;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Multi-Instance Control</h2>
        <button style={styles.refreshButton} onClick={fetchStatus} disabled={loading}>
          🔄 Refresh
        </button>
      </div>

      {error && (
        <div style={styles.errorAlert}>
          {error}
          <button style={styles.closeButton} onClick={() => setError(null)}>×</button>
        </div>
      )}

      {successMessage && (
        <div style={styles.successAlert}>
          {successMessage}
          <button style={styles.closeButton} onClick={() => setSuccessMessage(null)}>×</button>
        </div>
      )}

      {/* Settings Section */}
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Configuration</h3>
        <div style={styles.settingsGrid}>
          <div style={styles.settingItem}>
            <label style={styles.label}>
              <input
                type="checkbox"
                checked={settings.multi_instance.enabled}
                onChange={(e) => handleSettingsUpdate({ 
                  ...settings.multi_instance, 
                  enabled: e.target.checked 
                })}
                style={styles.checkbox}
              />
              Enable Multi-Instance Mode
            </label>
          </div>
          <div style={styles.settingItem}>
            <label style={styles.label}>
              <input
                type="checkbox"
                checked={settings.multi_instance.auto_start}
                onChange={(e) => handleSettingsUpdate({ 
                  ...settings.multi_instance, 
                  auto_start: e.target.checked 
                })}
                style={styles.checkbox}
              />
              Auto-Start on Launch
            </label>
          </div>
          <div style={styles.settingItem}>
            <label style={styles.label}>
              Number of Instances: {settings.multi_instance.default_instances}
            </label>
            <input
              type="range"
              min="1"
              max="8"
              value={settings.multi_instance.default_instances}
              onChange={(e) => handleSettingsUpdate({ 
                ...settings.multi_instance, 
                default_instances: parseInt(e.target.value) 
              })}
              disabled={loading}
              style={styles.slider}
            />
          </div>
          <div style={styles.buttonGroup}>
            <button
              style={styles.primaryButton}
              onClick={handleApplySettings}
              disabled={loading}
            >
              Apply Settings
            </button>
            <button
              style={styles.secondaryButton}
              onClick={() => handleInitialize(settings.multi_instance.default_instances)}
              disabled={loading}
            >
              ▶️ {status?.total_instances > 0 ? 'Restart' : 'Start'} Instances
            </button>
            <button
              style={styles.dangerButton}
              onClick={handleShutdown}
              disabled={loading || (status?.total_instances === 0)}
            >
              ⏹️ Stop All
            </button>
          </div>
        </div>
      </div>

      <hr style={styles.divider} />

      {/* Status Overview */}
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Status Overview</h3>
        <div style={styles.statusGrid}>
          <div style={styles.statusCard}>
            <div style={styles.statusNumber}>{status?.total_instances || 0}</div>
            <div style={styles.statusLabel}>Total</div>
          </div>
          <div style={styles.statusCard}>
            <div style={{ ...styles.statusNumber, color: '#4caf50' }}>{status?.available || 0}</div>
            <div style={styles.statusLabel}>Available</div>
          </div>
          <div style={styles.statusCard}>
            <div style={{ ...styles.statusNumber, color: '#ff9800' }}>{status?.busy || 0}</div>
            <div style={styles.statusLabel}>Busy</div>
          </div>
          <div style={styles.statusCard}>
            <div style={{ ...styles.statusNumber, color: '#f44336' }}>{status?.error || 0}</div>
            <div style={styles.statusLabel}>Error</div>
          </div>
        </div>
      </div>

      {/* Instance Details */}
      {instances.length > 0 && (
        <>
          <h3 style={styles.sectionTitle}>Instance Details</h3>
          <div style={styles.instanceGrid}>
            {instances.map((instance) => (
              <div key={instance.digit} style={styles.instanceCard}>
                <div style={styles.instanceHeader}>
                  <span style={styles.instanceTitle}>Instance {instance.digit}</span>
                  <span style={{ ...styles.instanceStatus, backgroundColor: getStatusColor(instance.status) }}>
                    {getStatusIcon(instance.status)} {instance.status}
                  </span>
                </div>
                <div style={styles.instanceDetails}>
                  <div>ML Port: {instance.ml_port}</div>
                  <div>DB Port: {instance.db_port}</div>
                  {instance.current_test && (
                    <div style={styles.currentTest}>Test: {instance.current_test}</div>
                  )}
                  <div style={styles.instanceStats}>
                    <span>💾 {instance.memory_mb.toFixed(0)} MB</span>
                    <span>⚡ {instance.cpu_percent.toFixed(0)}%</span>
                  </div>
                  <div style={styles.testCount}>Tests run: {instance.total_tests}</div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {loading && <div style={styles.loading}>Loading...</div>}
    </div>
  );
};

const styles = {
  container: {
    padding: '20px',
    backgroundColor: '#fff',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  },
  title: {
    margin: 0,
    fontSize: '24px',
    fontWeight: 'bold',
  },
  refreshButton: {
    padding: '8px 16px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: '#fff',
    cursor: 'pointer',
    fontSize: '14px',
  },
  errorAlert: {
    padding: '12px',
    backgroundColor: '#ffebee',
    border: '1px solid #ffcdd2',
    borderRadius: '4px',
    color: '#c62828',
    marginBottom: '16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  successAlert: {
    padding: '12px',
    backgroundColor: '#e8f5e9',
    border: '1px solid #c8e6c9',
    borderRadius: '4px',
    color: '#2e7d32',
    marginBottom: '16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    cursor: 'pointer',
    padding: '0 8px',
  },
  section: {
    marginBottom: '24px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 'bold',
    marginBottom: '16px',
  },
  settingsGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  settingItem: {
    marginBottom: '12px',
  },
  label: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '14px',
  },
  checkbox: {
    marginRight: '8px',
  },
  slider: {
    width: '100%',
    marginTop: '8px',
  },
  buttonGroup: {
    display: 'flex',
    gap: '8px',
    marginTop: '16px',
  },
  primaryButton: {
    padding: '8px 16px',
    backgroundColor: '#1976d2',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  secondaryButton: {
    padding: '8px 16px',
    backgroundColor: '#fff',
    color: '#1976d2',
    border: '1px solid #1976d2',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  dangerButton: {
    padding: '8px 16px',
    backgroundColor: '#fff',
    color: '#d32f2f',
    border: '1px solid #d32f2f',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  divider: {
    border: 'none',
    borderTop: '1px solid #ddd',
    margin: '24px 0',
  },
  statusGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '16px',
  },
  statusCard: {
    textAlign: 'center',
    padding: '16px',
    backgroundColor: '#f5f5f5',
    borderRadius: '4px',
  },
  statusNumber: {
    fontSize: '32px',
    fontWeight: 'bold',
  },
  statusLabel: {
    fontSize: '12px',
    color: '#666',
    marginTop: '4px',
  },
  instanceGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
    gap: '16px',
  },
  instanceCard: {
    border: '1px solid #ddd',
    borderRadius: '4px',
    padding: '16px',
  },
  instanceHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  instanceTitle: {
    fontWeight: 'bold',
  },
  instanceStatus: {
    padding: '4px 8px',
    borderRadius: '4px',
    color: 'white',
    fontSize: '12px',
  },
  instanceDetails: {
    fontSize: '14px',
    lineHeight: '1.6',
  },
  currentTest: {
    color: '#1976d2',
    marginTop: '4px',
  },
  instanceStats: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: '8px',
    fontSize: '12px',
  },
  testCount: {
    fontSize: '12px',
    color: '#666',
    marginTop: '4px',
  },
  loading: {
    textAlign: 'center',
    padding: '20px',
    color: '#666',
  },
};

export default InstanceControl;