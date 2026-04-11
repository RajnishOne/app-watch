import React, { useState } from 'react';
import { Icons } from './Icons';

export const FAVICON_PATH = '/icon-192.png';

export function Sidebar({ currentPage, onNavigate, appsCount, sidebarOpen, onCloseSidebar }) {
  const navItems = [
    { id: 'dashboard', label: 'Apps', icon: Icons.Apps, badge: appsCount },
    { id: 'add-app', label: 'Add App', icon: Icons.Add },
    { id: 'broadcast', label: 'Broadcast', icon: Icons.Broadcast },
    { id: 'activity', label: 'Activity', icon: Icons.Activity },
    { id: 'scheduler', label: 'Scheduler', icon: Icons.Clock },
    { id: 'settings', label: 'Settings', icon: Icons.Settings },
  ];

  return (
    <>
      <div className={`sidebar-overlay ${sidebarOpen ? 'visible' : ''}`} onClick={onCloseSidebar}></div>
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <img src={FAVICON_PATH} alt="App Watch" className="sidebar-logo" />
          <div className="sidebar-brand">
            <span className="sidebar-brand-name">App Watch</span>
            <span className="sidebar-brand-tagline">iOS Update Monitor</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section">
            <div className="nav-section-title">Navigation</div>
            {navItems.map(item => (
              <button
                key={item.id}
                className={`nav-item ${currentPage === item.id || (item.id === 'dashboard' && currentPage === 'edit-app') ? 'active' : ''}`}
                onClick={() => {
                  if (item.id === 'settings') {
                    onNavigate('settings', 'general');
                  } else {
                    onNavigate(item.id);
                  }
                  onCloseSidebar();
                }}
              >
                <item.icon />
                <span>{item.label}</span>
                {item.badge !== undefined && item.badge > 0 && (
                  <span className="nav-item-badge">{item.badge}</span>
                )}
              </button>
            ))}
          </div>
        </nav>
      </aside>
    </>
  );
}

export function AppLayout({ children, currentPage, onNavigate, appsCount }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-layout">
      <button className="sidebar-toggle" onClick={() => setSidebarOpen(true)}>
        <Icons.Menu />
      </button>

      <Sidebar
        currentPage={currentPage}
        onNavigate={onNavigate}
        appsCount={appsCount}
        sidebarOpen={sidebarOpen}
        onCloseSidebar={() => setSidebarOpen(false)}
      />

      <main className="main-content">
        {children}
      </main>
    </div>
  );
}
