import React, { useState, useEffect, useCallback } from 'react';
import { fetchHistoryQuery } from '../api';
import { Icons } from '../components/Icons';

export function SchedulerPage({ onCancel, apps, message, showMessage }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    app_id: '',
    status: '',
    search: ''
  });

  const loadHistory = useCallback(async (filterParams = {}) => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.append('limit', '500');
      params.append('event_type', 'scheduler_run');
      
      if (filterParams.app_id) params.append('app_id', filterParams.app_id);
      if (filterParams.status) params.append('status', filterParams.status);

      const data = await fetchHistoryQuery(params.toString());
      setHistory(data.history || []);
    } catch (error) {
      showMessage('Error loading scheduler history: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [showMessage]);

  useEffect(() => {
    loadHistory();
    document.title = 'Scheduler - App Watch';
    return () => { document.title = 'App Watch'; };
  }, [loadHistory]);

  const handleFilterChange = (name, value) => {
    const newFilters = { ...filters, [name]: value };
    setFilters(newFilters);
    loadHistory(newFilters);
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
          <p className="page-subtitle">Scheduled periodic checks and background job executions</p>
        </div>
      </div>

      <div className="page-content">
        <div className="filters-bar">
          <div className="filter-group">
            <label className="filter-label">App</label>
            <select
              value={filters.app_id}
              onChange={(e) => handleFilterChange('app_id', e.target.value)}
              className="form-select"
            >
              <option value="">All apps</option>
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
              <option value="">All status</option>
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
              placeholder="Filter messages…"
              className="form-input"
            />
          </div>
        </div>

        {loading ? (
          <div className="loading">
            <div className="loading-spinner"></div>
            <span>Loading scheduler history…</span>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <Icons.Clock />
            </div>
            <h3>No scheduler runs found</h3>
            <p>Scheduled check runs will appear here as the background scheduler executes</p>
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
                      <td className="font-mono text-muted text-nowrap">
                        {new Date(entry.timestamp).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'medium' })}
                      </td>
                      <td className="font-medium">{entry.app_name || '—'}</td>
                      <td>
                        <span className={`status-pill status-${entry.status}`}>
                          <span className="status-dot"></span>
                          {entry.status}
                        </span>
                      </td>
                      <td className="table-message-cell">{entry.message}</td>
                      <td className="font-mono text-muted">
                        {entry.details?.interval || '—'}
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
