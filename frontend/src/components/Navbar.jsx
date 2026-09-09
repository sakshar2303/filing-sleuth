import React from 'react';
import { ShieldCheck, Database, Sparkles, BookOpen, Home, Terminal } from 'lucide-react';

export default function Navbar({ isStreamingActive, serverHealthy, activeView, setActiveView }) {
  return (
    <header className="header-nav">
      {/* Brand & Edition */}
      <div 
        className="brand-badge" 
        onClick={() => setActiveView && setActiveView('welcome')} 
        style={{ cursor: 'pointer' }}
        title="Return to Welcome Tour"
      >
        <div className="logo-glow">
          <Sparkles size={18} color="#ffffff" />
        </div>
        <div className="brand-text-wrap">
          <span className="brand-title">FILING SLEUTH</span>
        </div>
        <span className="version-pill">SEC EDGAR</span>
      </div>

      {/* Primary View Switcher */}
      <nav className="nav-tab-switcher" aria-label="Primary Navigation">
        <button
          type="button"
          className={`nav-tab-btn ${activeView === 'welcome' ? 'active' : ''}`}
          onClick={() => setActiveView('welcome')}
          title="Product Tour & Overview"
        >
          <Home size={14} />
          <span>Tour</span>
        </button>
        <button
          type="button"
          className={`nav-tab-btn ${activeView === 'workspace' ? 'active' : ''}`}
          onClick={() => setActiveView('workspace')}
          title="SEC Financial Research Terminal"
        >
          <Terminal size={14} />
          <span className="tab-label-full">Research Terminal</span>
          <span className="tab-label-short">Terminal</span>
        </button>
        <button
          type="button"
          className={`nav-tab-btn ${activeView === 'about' ? 'active' : ''}`}
          onClick={() => setActiveView('about')}
          title="Architecture & 3D Model"
        >
          <BookOpen size={14} />
          <span className="tab-label-full">Methodology & 3D</span>
          <span className="tab-label-short">Methodology</span>
        </button>
      </nav>

      {/* System Status & Verification Badges */}
      <div className="status-indicators">
        <div className="status-tag xbrl-badge" title="Official SEC CompanyFacts XBRL machine tags prioritized over prose">
          <Database size={14} color="#0284c7" />
          <span className="badge-text-full">XBRL Ground Truth</span>
          <span className="badge-text-short">XBRL</span>
        </div>
        <div className="status-tag audit-badge" title="Strict fuzzy quote verification via sliding window Levenshtein matcher (>85%)">
          <ShieldCheck size={14} color="#0f766e" />
          <span className="badge-text-full">Zero Hallucination</span>
          <span className="badge-text-short">Audited</span>
        </div>
        <div className="status-tag server-status-badge" title={serverHealthy ? 'FastAPI Agent Engine Operational' : 'Connecting to SEC EDGAR Agent...'}>
          <div className="status-dot" style={{ backgroundColor: serverHealthy ? '#0f766e' : '#d97706' }} />
          <span>{isStreamingActive ? 'Streaming' : serverHealthy ? 'Agent Online' : 'Connecting...'}</span>
        </div>
      </div>
    </header>
  );
}



