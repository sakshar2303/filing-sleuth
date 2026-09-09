import React from 'react';
import {
  Home,
  Terminal,
  BookOpen,
  History,
  Clock,
  Plus,
  PanelLeftClose,
  PanelLeftOpen,
  Database,
  Trash2,
  ArrowUpRight
} from 'lucide-react';
import BrandLogo from './BrandLogo';

const WATCHLIST = [
  { ticker: 'AAPL', name: 'Apple' },
  { ticker: 'MSFT', name: 'Microsoft' },
  { ticker: 'NVDA', name: 'NVIDIA' },
  { ticker: 'TSLA', name: 'Tesla' },
  { ticker: 'AMZN', name: 'Amazon' },
  { ticker: 'GOOGL', name: 'Alphabet' },
];

export default function Sidebar({
  activeView,
  setActiveView,
  isCollapsed,
  setIsCollapsed,
  history = [],
  onSelectHistory,
  onClearHistory,
  onNewQuery,
  onSelectTicker,
}) {
  return (
    <aside className={`analyst-sidebar ${isCollapsed ? 'collapsed' : 'expanded'}`}>
      {/* Sidebar Header */}
      <div className="sidebar-top">
        {!isCollapsed ? (
          <div className="sidebar-brand" onClick={() => setActiveView('welcome')}>
            <div className="sidebar-logo">
              <BrandLogo size={22} animated />
            </div>
            <span className="sidebar-brand-text">FILING SLEUTH</span>
          </div>
        ) : (
          <div className="sidebar-brand-collapsed" onClick={() => setActiveView('welcome')} title="Filing Sleuth">
            <BrandLogo size={24} animated />
          </div>
        )}

        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? 'Expand Sidebar (Cmd+B)' : 'Collapse Sidebar (Cmd+B)'}
        >
          {isCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      {/* New Query Action */}
      <div className="sidebar-action-wrap">
        <button
          type="button"
          className="sidebar-new-btn"
          onClick={onNewQuery}
          title="Start fresh research session"
        >
          <Plus size={16} />
          {!isCollapsed && <span>New Research</span>}
        </button>
      </div>

      {/* Primary Navigation Views */}
      <div className="sidebar-section">
        {!isCollapsed && <div className="sidebar-section-title">Navigation</div>}
        <nav className="sidebar-nav">
          <button
            type="button"
            className={`sidebar-nav-item ${activeView === 'welcome' ? 'active' : ''}`}
            onClick={() => setActiveView('welcome')}
            title="Welcome & Product Tour"
          >
            <Home size={17} />
            {!isCollapsed && <span>Welcome & Tour</span>}
          </button>

          <button
            type="button"
            className={`sidebar-nav-item ${activeView === 'workspace' ? 'active' : ''}`}
            onClick={() => setActiveView('workspace')}
            title="Research Workspace"
          >
            <Terminal size={17} />
            {!isCollapsed && <span>Research Terminal</span>}
          </button>

          <button
            type="button"
            className={`sidebar-nav-item ${activeView === 'about' ? 'active' : ''}`}
            onClick={() => setActiveView('about')}
            title="Architecture & Methodology"
          >
            <BookOpen size={17} />
            {!isCollapsed && <span>Methodology & 3D</span>}
          </button>
        </nav>
      </div>

      {/* Recent Sessions History */}
      {!isCollapsed && (
        <div className="sidebar-section sidebar-history-section">
          <div className="sidebar-section-title-row">
            <span className="sidebar-section-title">Recent Sessions</span>
            {history.length > 0 && (
              <button
                type="button"
                className="sidebar-clear-btn"
                onClick={onClearHistory}
                title="Clear query history"
              >
                <Trash2 size={12} />
              </button>
            )}
          </div>

          <div className="sidebar-history-list">
            {history.length === 0 ? (
              <div className="sidebar-empty-history">
                <Clock size={14} />
                <span>No recent queries yet</span>
              </div>
            ) : (
              history.map((item) => (
                <div
                  key={item.id}
                  className="sidebar-history-item"
                  onClick={() => onSelectHistory(item)}
                  title={item.question}
                >
                  <Clock size={13} className="history-clock-icon" />
                  <span className="history-text">{item.question}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Quick Registrant Watchlist */}
      {!isCollapsed && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Monitored Registrants</div>
          <div className="sidebar-watchlist-grid">
            {WATCHLIST.map((w) => (
              <button
                key={w.ticker}
                type="button"
                className="sidebar-watchlist-chip"
                onClick={() => onSelectTicker(w.ticker, w.name)}
                title={`Research ${w.name} (${w.ticker})`}
              >
                <span className="watchlist-ticker">{w.ticker}</span>
                <span className="watchlist-name">{w.name}</span>
                <ArrowUpRight size={10} className="watchlist-arrow" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Sidebar Footer Status */}
      <div className="sidebar-footer">
        <div className="sidebar-status-badge">
          <div className="status-dot" style={{ backgroundColor: '#10b981' }} />
          {!isCollapsed && <span>EDGAR API Online</span>}
        </div>
      </div>
    </aside>
  );
}
