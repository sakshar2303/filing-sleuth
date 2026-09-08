import React from 'react';
import {
  TrendingUp,
  ShieldAlert,
  BarChart3,
  ArrowRight,
  Sparkles,
  Database,
  CheckCircle2,
  Lock,
  Cpu
} from 'lucide-react';
import TiltCard from './TiltCard';

const PLAYBOOKS = [
  {
    id: 'rd-battle',
    icon: <BarChart3 size={20} color="#0f766e" />,
    badge: 'Peer Benchmarking',
    title: 'The Big Tech R&D Intensity Race',
    subtitle: 'Cross-reference R&D spend as % of revenue between Apple and Microsoft across 10-K filings.',
    query: 'Compare R&D spend as % of revenue between Apple and Microsoft over the last 2 years.',
    tag: 'XBRL Facts + Basis Point Spread',
    gradient: 'linear-gradient(135deg, rgba(15, 118, 110, 0.08) 0%, rgba(2, 132, 199, 0.06) 100%)',
  },
  {
    id: 'tesla-credits',
    icon: <TrendingUp size={20} color="#0284c7" />,
    badge: 'Longitudinal Trend',
    title: 'Tesla Regulatory Credit Arbitrage',
    subtitle: 'Extract automotive regulatory credits across 3 annual filings and compute YoY growth rate.',
    query: 'How has Tesla\'s automotive regulatory credits revenue trended over the last 3 fiscal years?',
    tag: 'Multi-Period Dedup + YoY Math',
    gradient: 'linear-gradient(135deg, rgba(2, 132, 199, 0.08) 0%, rgba(99, 102, 241, 0.06) 100%)',
  },
  {
    id: 'cyber-dma',
    icon: <ShieldAlert size={20} color="#7c3aed" />,
    badge: 'Item 1C / 1A Forensic Audit',
    title: 'Enterprise Cybersecurity Governance',
    subtitle: 'Audit Microsoft\'s newly mandated Item 1C disclosures for board oversight and incident response.',
    query: 'What cybersecurity risk management and governance did Microsoft disclose in Item 1C?',
    tag: 'Structure-Aware Hybrid + Quote Audit',
    gradient: 'linear-gradient(135deg, rgba(124, 58, 237, 0.08) 0%, rgba(219, 39, 119, 0.06) 100%)',
  },
];

export default function AnalystLaunchpad({ onSelectQuery, disabled }) {
  return (
    <div className="launchpad-container">
      {/* Platform Stats Ribbon */}
      <div className="launchpad-stats-banner">
        <div className="launchpad-stat-item">
          <div className="launchpad-stat-num">10,412</div>
          <div className="launchpad-stat-desc">
            <Database size={13} color="var(--accent-primary)" />
            <span>SEC Public Filers Indexed</span>
          </div>
        </div>

        <div className="launchpad-stat-divider" />

        <div className="launchpad-stat-item">
          <div className="launchpad-stat-num">20 / 20</div>
          <div className="launchpad-stat-desc">
            <CheckCircle2 size={13} color="#059669" />
            <span>Benchmark Accuracy (100%)</span>
          </div>
        </div>

        <div className="launchpad-stat-divider" />

        <div className="launchpad-stat-item">
          <div className="launchpad-stat-num">0.0%</div>
          <div className="launchpad-stat-desc">
            <Lock size={13} color="#0284c7" />
            <span>Zero Hallucination Rate</span>
          </div>
        </div>

        <div className="launchpad-stat-divider" />

        <div className="launchpad-stat-item">
          <div className="launchpad-stat-num">&gt;85%</div>
          <div className="launchpad-stat-desc">
            <Sparkles size={13} color="#7c3aed" />
            <span>Quote Fuzzy Verification Threshold</span>
          </div>
        </div>
      </div>

      {/* Featured Dossiers Section */}
      <div className="launchpad-section-header">
        <div className="launchpad-section-title">
          <Sparkles size={18} color="var(--accent-primary)" />
          <span>Featured Research Playbooks</span>
        </div>
        <p className="launchpad-section-sub">
          Select a verified analyst dossier below or enter custom ticker queries above to initiate research.
        </p>
      </div>

      <div className="playbooks-grid">
        {PLAYBOOKS.map((pb) => (
          <TiltCard
            key={pb.id}
            className="playbook-card"
            maxTilt={5}
            scale={1.015}
            style={{ background: pb.gradient }}
          >
            <div className="playbook-top">
              <div className="playbook-icon-box">{pb.icon}</div>
              <span className="playbook-badge">{pb.badge}</span>
            </div>

            <h3 className="playbook-title">{pb.title}</h3>
            <p className="playbook-subtitle">{pb.subtitle}</p>

            <div className="playbook-footer">
              <span className="playbook-tag">{pb.tag}</span>
              <button
                type="button"
                className="playbook-run-btn"
                onClick={() => !disabled && onSelectQuery(pb.query)}
                disabled={disabled}
              >
                <span>Launch</span>
                <ArrowRight size={13} />
              </button>
            </div>
          </TiltCard>
        ))}
      </div>
    </div>
  );
}
