import React, { useState, useEffect } from 'react';
import { Icons } from './Icons';

export const FAVICON_PATH = '/icon-192.png';

export function DonateModal({ isOpen, onClose }) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="donate-modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="donate-modal-title"
    >
      <div className="donate-modal" onClick={(e) => e.stopPropagation()}>
        <div className="donate-modal-header">
          <div className="donate-modal-header-left">
            <div className="donate-modal-heart-icon">
              <Icons.Heart />
            </div>
            <div>
              <h3 id="donate-modal-title" className="donate-modal-title">Support App Watch</h3>
              <p className="donate-modal-subtitle">Open-source App Update Monitor</p>
            </div>
          </div>
          <button
            type="button"
            className="donate-modal-close-btn"
            onClick={onClose}
            aria-label="Close donation modal"
          >
            <Icons.Close />
          </button>
        </div>

        <div className="donate-modal-body">
          <p className="donate-modal-text">
            App Watch is free and open-source. If it helps you track app updates, consider supporting its development through any of the options below!
          </p>

          <div className="donate-modal-options">
            <a
              href="https://ko-fi.com/rajnishone"
              target="_blank"
              rel="noopener noreferrer"
              className="donate-modal-card kofi-card"
            >
              <div className="donate-modal-card-icon kofi-icon">
                <Icons.Kofi />
              </div>
              <div className="donate-modal-card-content">
                <div className="donate-modal-card-title">Support on Ko-fi</div>
                <div className="donate-modal-card-desc">Buy a coffee or tip via Card / PayPal</div>
              </div>
              <div className="donate-modal-card-arrow">
                <Icons.ExternalLink />
              </div>
            </a>

            <a
              href="https://github.com/sponsors/rajnishone"
              target="_blank"
              rel="noopener noreferrer"
              className="donate-modal-card github-card"
            >
              <div className="donate-modal-card-icon github-icon">
                <Icons.GitHub />
              </div>
              <div className="donate-modal-card-content">
                <div className="donate-modal-card-title">GitHub Sponsors</div>
                <div className="donate-modal-card-desc">One-time or monthly sponsorship</div>
              </div>
              <div className="donate-modal-card-arrow">
                <Icons.ExternalLink />
              </div>
            </a>
          </div>

          <div className="donate-modal-footer-note">
            Thank you for supporting open source! ❤️
          </div>
        </div>
      </div>
    </div>
  );
}

export function Sidebar({ currentPage, onNavigate, appsCount, sidebarOpen, onCloseSidebar }) {
  const [donateOpen, setDonateOpen] = useState(false);

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
            <span className="sidebar-brand-tagline">App Update Monitor</span>
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

        <div className="sidebar-footer">
          <div className="sidebar-footer-links">
            <a
              href="https://github.com/RajnishOne/app-watch"
              target="_blank"
              rel="noopener noreferrer"
              className="sidebar-footer-btn"
              title="View App Watch on GitHub"
            >
              <Icons.GitHub />
              <span>GitHub</span>
            </a>
            <button
              type="button"
              className="sidebar-footer-btn donate-btn"
              onClick={() => setDonateOpen(true)}
              title="Support App Watch development"
            >
              <Icons.Heart />
              <span>Donate</span>
            </button>
          </div>
        </div>
      </aside>

      <DonateModal isOpen={donateOpen} onClose={() => setDonateOpen(false)} />
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
