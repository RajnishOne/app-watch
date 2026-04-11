import React, { useState, useEffect } from 'react';
import { fetchHistoryQuery } from '../api';

export function SchedulerPage({ onCancel, apps, message, showMessage }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    app_id: '',
    status: '',
    search: ''
  });

  useEffect(() => {
    loadHistory();
    document.title = 'Scheduler - App Watch';
    return () => { document.title = 'App Watch'; };
  }, []);

  const loadHistory = async (filterParams = {}) => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.append('limit', '500');
      params.append('event_type', 'scheduler_run'); // Only scheduler runs
      
      if (filterParams.app_id || filters.app_id) params.append('app_id', filterParams.app_id || filters.app_id);
      if (filterParams.status || filters.status) params.append('status', filterParams.status || filters.status);

      const response = await fetchHistoryQuery(params.toString());
      if (response.ok) {
        const data = await response.json();
        setHistory(data.history || []);
      } else {
        showMessage('Failed to load scheduler history', 'error');
      }
    } catch (error) {
      showMessage('Error loading scheduler history: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (name, value) => {
    const newFilters = { ...filters, [name]: value };
    setFilters(newFilters);
    loadHistory(newFilters);
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success': return '✓';
      case 'error': return '✗';
      case 'warning': return '⚠';
      default: return 'ℹ';
    }
  };

  const filteredHistory = history.filter(entry => {
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      return (
        entry.message?.toLowerCase().includes(searchLower) ||
        entry.app_name?.toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Scheduler</h1>
          <p className="page-subtitle">View scheduled check runs and their status</p>
        </div>
      </div>

      <div className="page-content">
        {message && (
          <div className={`alert alert-${message.type}`}>
            {message.text}
          </div>
        )}

        <div className="filters-bar">
          <div className="filter-group">
            <label className="filter-label">App</label>
            <select
              value={filters.app_id}
              onChange={(e) => handleFilterChange('app_id', e.target.value)}
              className="form-select"
            >
              <option value="">All Apps</option>
              {apps.map(app => (
                <option key={app.id} value={app.id}>{app.name}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Status</label>
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="form-select"
            >
              <option value="">All Status</option>
              <option value="success">Success</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Search</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              placeholder="Search messages..."
              className="form-input"
            />
          </div>
        </div>

        {loading ? (
          <div className="loading">
            <div className="loading-spinner"></div>
            <span>Loading scheduler history...</span>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">⏰</div>
            <h3>No scheduler runs found</h3>
            <p>Scheduled check runs will appear here when the scheduler triggers app checks</p>
          </div>
        ) : (
          <div className="card">
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>App</th>
                    <th>Status</th>
                    <th>Message</th>
                    <th>Interval</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredHistory.map((entry) => (
                    <tr key={entry.id}>
                      <td style={{ whiteSpace: 'nowrap' }}>
                        {new Date(entry.timestamp).toLocaleString()}
                      </td>
                      <td>{entry.app_name || '-'}</td>
                      <td>
                        <span className={`status-badge status-${entry.status}`}>
                          {getStatusIcon(entry.status)} {entry.status}
                        </span>
                      </td>
                      <td>{entry.message}</td>
                      <td>
                        {entry.details?.interval || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
