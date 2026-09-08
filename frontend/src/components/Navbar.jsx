import React from 'react';
import { ShieldCheck, Activity, Database, Sparkles, BookOpen, Compass, Search, Home, Terminal, PanelLeft } from 'lucide-react';

export default function Navbar({ isStreamingActive, serverHealthy, activeView, setActiveView, onToggleSidebar, isSidebarCollapsed }) {
  return (
    <header className="header-nav">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <button
          type="button"
          className="navbar-sidebar-toggle"
          onClick={onToggleSidebar}
          title={isSidebarCollapsed ? 'Open Sidebar (Cmd+B)' : 'Close Sidebar (Cmd+B)'}
        >
          <PanelLeft size={18} />
        </button>

        <div className="brand-badge" onClick={() => setActiveView && setActiveView('welcome')} style={{ cursor: 'pointer' }}>
          <div className="logo-glow">
            <Sparkles size={18} color="#ffffff" />
          </div>
          <div>
            <span className="brand-title">FILING SLEUTH</span>
          </div>
          <span className="version-pill">SEC EDGAR</span>
        </div>
      </div>

      {/* Navigation View Switcher */}
      <div className="nav-tab-switcher">
        <button
          className={`nav-tab-btn ${activeView === 'welcome' ? 'active' : ''}`}
          onClick={() => setActiveView('welcome')}
        >
          <Home size={14} />
          <span>Tour</span>
        </button>
        <button
          className={`nav-tab-btn ${activeView === 'workspace' ? 'active' : ''}`}
          onClick={() => setActiveView('workspace')}
        >
          <Terminal size={14} />
          <span>Research Terminal</span>
        </button>
        <button
          className={`nav-tab-btn ${activeView === 'about' ? 'active' : ''}`}
          onClick={() => setActiveView('about')}
        >
          <BookOpen size={14} />
          <span>Methodology & 3D</span>
        </button>
      </div>

      <div className="status-indicators">
        <div className="status-tag" title="Ground truth SEC facts prioritized over prose parsing">
          <Database size={15} color="#0284c7" />
          <span>XBRL Ground Truth</span>
        </div>
        <div className="status-tag" title="Strict quote verification via fuzzy sliding window token matching">
          <ShieldCheck size={15} color="#0f766e" />
          <span>Zero Hallucination</span>
        </div>
        <div className="status-tag">
          <div className="status-dot" style={{ backgroundColor: serverHealthy ? '#0f766e' : '#d97706' }} />
          <span>{isStreamingActive ? 'Pipeline Streaming' : serverHealthy ? 'Agent Online' : 'Connecting...'}</span>
        </div>
      </div>
    </header>
  );
}


