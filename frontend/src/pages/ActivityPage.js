import React, { useState, useEffect } from 'react';
import { fetchHistoryQuery } from '../api';

export function ActivityPage({ onCancel, apps, message, showMessage }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    event_type: '',
    app_id: '',
    status: '',
    search: ''
  });

  useEffect(() => {
    loadHistory();
    document.title = 'Activity - App Watch';
    return () => { document.title = 'App Watch'; };
  }, []);

  const loadHistory = async (filterParams = {}) => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.append('limit', '200');
      
      if (filterParams.event_type || filters.event_type) params.append('event_type', filterParams.event_type || filters.event_type);
      if (filterParams.app_id || filters.app_id) params.append('app_id', filterParams.app_id || filters.app_id);
      if (filterParams.status || filters.status) params.append('status', filterParams.status || filters.status);

      const response = await fetchHistoryQuery(params.toString());
      if (response.ok) {
        const data = await response.json();
        setHistory(data.history || []);
      } else {
        showMessage('Failed to load activity history', 'error');
      }
    } catch (error) {
      showMessage('Error loading activity: ' + error.message, 'error');
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

  const getEventTypeLabel = (eventType) => {
    const labels = {
      'check': 'Check',
      'post': 'Post',
      'scheduler_run': 'Scheduler Run',
      'app_created': 'App Created',
      'app_updated': 'App Updated',
      'app_deleted': 'App Deleted',
      'app_enabled': 'App Enabled',
      'app_disabled': 'App Disabled',
      'settings_updated': 'Settings Updated'
    };
    return labels[eventType] || eventType;
  };

  const filteredHistory = history.filter(entry => {
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      return (
        entry.message?.toLowerCase().includes(searchLower) ||
        entry.app_name?.toLowerCase().includes(searchLower) ||
        entry.event_type?.toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Activity</h1>
          <p className="page-subtitle">View app monitoring history and events</p>
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
            <label className="filter-label">Event Type</label>
            <select
              value={filters.event_type}
              onChange={(e) => handleFilterChange('event_type', e.target.value)}
              className="form-select"
            >
              <option value="">All Events</option>
              <option value="check">Check</option>
              <option value="post">Post</option>
              <option value="scheduler_run">Scheduler Run</option>
              <option value="app_created">App Created</option>
              <option value="app_updated">App Updated</option>
              <option value="app_deleted">App Deleted</option>
            </select>
          </div>

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
            <span>Loading activity...</span>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <h3>No activity found</h3>
            <p>Activity history will appear here as you use the application</p>
          </div>
        ) : (
          <div className="card">
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Event</th>
                    <th>App</th>
                    <th>Status</th>
                    <th>Message</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredHistory.map((entry) => (
                    <tr key={entry.id}>
                      <td style={{ whiteSpace: 'nowrap' }}>
                        {new Date(entry.timestamp).toLocaleString()}
                      </td>
                      <td>
                        <span className="status-badge status-info">
                          {getEventTypeLabel(entry.event_type)}
                        </span>
                      </td>
                      <td>{entry.app_name || '-'}</td>
                      <td>
                        <span className={`status-badge status-${entry.status}`}>
                          {getStatusIcon(entry.status)} {entry.status}
                        </span>
                      </td>
                      <td>{entry.message}</td>
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
