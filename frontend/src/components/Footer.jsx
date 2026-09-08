import React from 'react';
import { ShieldCheck, Database, GitBranch, ExternalLink, Sparkles, Terminal } from 'lucide-react';

export default function Footer({ onSwitchView }) {
  return (
    <footer className="footer-container">
      <div className="footer-inner">
        <div className="footer-brand-col">
          <div className="footer-brand-row">
            <div className="footer-logo">
              <Sparkles size={16} color="#ffffff" />
            </div>
            <span className="footer-brand-name">FILING SLEUTH</span>
            <span className="footer-version-tag">v1.0.0</span>
          </div>
          <p className="footer-disclaimer">
            Forensic SEC EDGAR intelligence platform. Built for equity research analysts, auditors, and journalists.
            All data extracted directly from official SEC CompanyFacts XBRL endpoints and audited against raw 10-K filings.
          </p>
        </div>

        <div className="footer-links-col">
          <div className="footer-col-title">Navigation</div>
          <button type="button" className="footer-link-btn" onClick={() => onSwitchView('workspace')}>
            Research Workspace
          </button>
          <button type="button" className="footer-link-btn" onClick={() => onSwitchView('about')}>
            System Architecture & Methodology
          </button>
        </div>

        <div className="footer-links-col">
          <div className="footer-col-title">Resources & Provenance</div>
          <a
            href="https://github.com/sakshar2303/filing-sleuth"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-external-link"
          >
            <GitBranch size={14} />
            <span>GitHub Repository</span>
            <ExternalLink size={12} />
          </a>

          <a
            href="https://www.sec.gov/edgar/searchedgar/companysearch"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-external-link"
          >
            <Database size={14} />
            <span>SEC EDGAR Archives</span>
            <ExternalLink size={12} />
          </a>
        </div>
      </div>

      <div className="footer-bottom-bar">
        <div className="footer-status-pill">
          <div className="footer-status-dot" />
          <span>SEC Submissions API & ChromaDB Hybrid Search Operational</span>
        </div>
        <div className="footer-copy">
          © {new Date().getFullYear()} Filing Sleuth · Open Source Financial Forensic Agent
        </div>
      </div>
    </footer>
  );
}
