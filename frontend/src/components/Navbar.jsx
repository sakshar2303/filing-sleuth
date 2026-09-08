import React from 'react';
import { ShieldCheck, Activity, Database, Sparkles } from 'lucide-react';

export default function Navbar({ isStreamingActive, serverHealthy }) {
  return (
    <header className="header-nav">
      <div className="brand-badge">
        <div className="logo-glow">
          <Sparkles size={20} color="#ffffff" />
        </div>
        <div>
          <span className="brand-title">FILING SLEUTH</span>
        </div>
        <span className="version-pill">SEC EDGAR AI AGENT</span>
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
