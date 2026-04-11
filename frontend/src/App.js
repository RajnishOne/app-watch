import React, { useState, useEffect, useRef } from 'react';
import './index.css';
import { applyAccentToDocument, getSavedAccent } from './theme';
import {
  fetchApps,
  deleteApp,
  checkApp,
  postApp,
  saveAppRequest
} from './api';
import { getHumanReadableError } from './utils/errors';
import { AppLayout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { AddAppPage } from './pages/AddAppPage';
import { SettingsPage } from './pages/SettingsPage';
import { ActivityPage } from './pages/ActivityPage';
import { SchedulerPage } from './pages/SchedulerPage';
import { SendWebhookPage } from './pages/SendWebhookPage';

function App() {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [editingApp, setEditingApp] = useState(null);
  const [message, setMessage] = useState(null);
  const [checking, setChecking] = useState({});
  const [posting, setPosting] = useState({});

  // Ref to track if apps have been loaded to prevent duplicate calls
  const appsLoadedRef = useRef(false);
  const loadingAppsRef = useRef(false);

  // Theme state
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem('app_theme');
    return savedTheme || 'dark';
  });

  // Accent color state
  const [accent, setAccent] = useState(getSavedAccent);

  const [settingsSection, setSettingsSection] = useState('general');

  // Apply theme on mount and when theme changes
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('app_theme', theme);
  }, [theme]);

  // Apply accent on mount and when accent changes
  useEffect(() => {
    applyAccentToDocument(accent);
    localStorage.setItem('app_accent', accent);
  }, [accent]);

  useEffect(() => {
    localStorage.removeItem('auth_token');
  }, []);

  useEffect(() => {
    const checkRoute = () => {
      const path = window.location.pathname;
      if (path === '/add-app' || path.includes('/add-app')) {
        setCurrentPage('add-app');
        setEditingApp(null);
      } else if (path.includes('/edit-app/')) {
        setCurrentPage('edit-app');
        const appId = path.split('/edit-app/')[1];
        if (appId && !editingApp) {
          (async () => {
            try {
              const apps = await fetchApps();
              const app = apps.find((a) => a.id === appId);
              if (app) {
                setEditingApp(app);
              } else {
                setCurrentPage('dashboard');
                setEditingApp(null);
                window.history.replaceState({ page: 'dashboard' }, '', '/');
              }
            } catch {
              setCurrentPage('dashboard');
              setEditingApp(null);
              window.history.replaceState({ page: 'dashboard' }, '', '/');
            }
          })();
        }
      } else if (path === '/settings' || path.includes('/settings')) {
        setCurrentPage('settings');
        // Extract section from path
        const sectionMatch = path.match(/\/settings\/(\w+)/);
        if (sectionMatch) {
          setSettingsSection(sectionMatch[1]);
        } else {
          setSettingsSection('general');
        }
      } else if (path === '/activity' || path.includes('/activity')) {
        setCurrentPage('activity');
      } else if (path === '/scheduler' || path.includes('/scheduler')) {
        setCurrentPage('scheduler');
      } else if (path === '/broadcast' || path.includes('/broadcast')) {
        setCurrentPage('broadcast');
      } else {
        setCurrentPage('dashboard');
        setEditingApp(null);
      }
    };

    checkRoute();

    const handlePopState = () => checkRoute();
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [editingApp]);

  const loadApps = async () => {
    if (loadingAppsRef.current) return;

    try {
      loadingAppsRef.current = true;
      setLoading(true);
      const data = await fetchApps();
      setApps(data);
      appsLoadedRef.current = true;
    } catch (error) {
      const friendlyError = getHumanReadableError(error.message || 'Network error occurred');
      showMessage(friendlyError, 'error');
    } finally {
      setLoading(false);
      loadingAppsRef.current = false;
    }
  };

  useEffect(() => {
    loadApps();
  }, []);

  const showMessage = (text, type = 'success') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 5000);
  };

  const handleNavigate = (page, section = null) => {
    if (page === 'dashboard') {
      setCurrentPage('dashboard');
      setEditingApp(null);
      window.history.pushState({ page: 'dashboard' }, '', '/');
    } else if (page === 'add-app') {
      setEditingApp(null);
      setCurrentPage('add-app');
      window.history.pushState({ page: 'add-app' }, '', '/add-app');
    } else if (page === 'settings') {
      setCurrentPage('settings');
      setSettingsSection(section || 'general');
      const sectionPath = section && section !== 'general' ? `/${section}` : '';
      window.history.pushState({ page: 'settings', section }, '', `/settings${sectionPath}`);
    } else if (page === 'activity') {
      setCurrentPage('activity');
      window.history.pushState({ page: 'activity' }, '', '/activity');
    } else if (page === 'scheduler') {
      setCurrentPage('scheduler');
      window.history.pushState({ page: 'scheduler' }, '', '/scheduler');
    } else if (page === 'broadcast') {
      setCurrentPage('broadcast');
      window.history.pushState({ page: 'broadcast' }, '', '/broadcast');
    }
  };

  const handleEditApp = (app) => {
    setEditingApp(app);
    setCurrentPage('edit-app');
    window.history.pushState({ page: 'edit-app' }, '', `/edit-app/${app.id}`);
  };

  const handleDeleteApp = async (appId) => {
    if (!window.confirm('Are you sure you want to delete this app?')) return;

    try {
      await deleteApp(appId);
      showMessage('App deleted successfully');
      appsLoadedRef.current = false;
      loadApps();
    } catch (error) {
      const friendlyError = getHumanReadableError(error.message || 'Network error occurred');
      showMessage(friendlyError, 'error');
    }
  };

  const handleCheckApp = async (appId) => {
    setChecking({ ...checking, [appId]: true });
    try {
      const data = await checkApp(appId);
      if (data.success) {
        showMessage(data.message || 'Check completed successfully', 'success');
      } else {
        const friendlyError = getHumanReadableError(data.error);
        showMessage(friendlyError, 'error');
      }
      appsLoadedRef.current = false;
      loadApps();
    } catch (error) {
      const friendlyError = getHumanReadableError(error.message || 'Network error occurred');
      showMessage(friendlyError, 'error');
    } finally {
      setChecking({ ...checking, [appId]: false });
    }
  };

  const handlePostApp = async (appId) => {
    setPosting({ ...posting, [appId]: true });
    try {
      const data = await postApp(appId);
      if (data.success) {
        showMessage(data.message || 'Posted successfully', 'success');
      } else {
        const friendlyError = getHumanReadableError(data.error);
        showMessage(friendlyError, 'error');
      }
      appsLoadedRef.current = false;
      loadApps();
    } catch (error) {
      const friendlyError = getHumanReadableError(error.message || 'Network error occurred');
      showMessage(friendlyError, 'error');
    } finally {
      setPosting({ ...posting, [appId]: false });
    }
  };

  const handleSaveApp = async (formData) => {
    try {
      const appId = formData.id || editingApp?.id;
      await saveAppRequest(appId, formData);
      showMessage(appId ? 'App updated successfully' : 'App added successfully');
      setCurrentPage('dashboard');
      setEditingApp(null);
      window.history.pushState({ page: 'dashboard' }, '', '/');
      appsLoadedRef.current = false;
      loadApps();
    } catch (error) {
      const friendlyError = getHumanReadableError(error.message || 'Network error occurred');
      showMessage(friendlyError, 'error');
    }
  };

  if (loading) {
    return (
      <AppLayout
        currentPage={currentPage}
        onNavigate={handleNavigate}
        appsCount={0}
      >
        <div className="page-content">
          <div className="loading">
            <div className="loading-spinner"></div>
            <span>Loading apps...</span>
          </div>
        </div>
      </AppLayout>
    );
  }

  // Render content based on current page
  const renderContent = () => {
    switch (currentPage) {
      case 'add-app':
        return (
          <AddAppPage
            onSave={handleSaveApp}
            onCancel={() => handleNavigate('dashboard')}
            message={message}
            showMessage={showMessage}
            editingApp={null}
          />
        );
      case 'edit-app':
        return editingApp ? (
          <AddAppPage
            onSave={handleSaveApp}
            onCancel={() => handleNavigate('dashboard')}
            message={message}
            showMessage={showMessage}
            editingApp={editingApp}
          />
        ) : null;
      case 'settings':
        return (
          <SettingsPage
            onCancel={() => handleNavigate('dashboard')}
            message={message}
            showMessage={showMessage}
            section={settingsSection}
            onNavigateSection={(section) => handleNavigate('settings', section)}
            theme={theme}
            onThemeChange={setTheme}
            accent={accent}
            onAccentChange={setAccent}
          />
        );
      case 'activity':
        return (
          <ActivityPage
            onCancel={() => handleNavigate('dashboard')}
            apps={apps}
            message={message}
            showMessage={showMessage}
          />
        );
      case 'scheduler':
        return (
          <SchedulerPage
            onCancel={() => handleNavigate('dashboard')}
            apps={apps}
            message={message}
            showMessage={showMessage}
          />
        );
      case 'broadcast':
        return (
          <SendWebhookPage
            onCancel={() => handleNavigate('dashboard')}
            message={message}
            showMessage={showMessage}
          />
        );
      default:
        return (
          <DashboardPage
            apps={apps}
            message={message}
            onAddApp={() => handleNavigate('add-app')}
            onEditApp={handleEditApp}
            onDeleteApp={handleDeleteApp}
            onCheckApp={handleCheckApp}
            onPostApp={handlePostApp}
            checking={checking}
            posting={posting}
          />
        );
    }
  };

  return (
    <AppLayout
      currentPage={currentPage}
      onNavigate={handleNavigate}
      appsCount={apps.length}
    >
      {renderContent()}
    </AppLayout>
  );
}

export default App;
