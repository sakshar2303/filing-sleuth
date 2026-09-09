import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  TrendingDown,
  Info,
  ChevronDown,
  ChevronUp,
  Activity,
  Zap,
} from 'lucide-react';

export default function ForensicRadar({ scorecard, skepticMode }) {
  const [expandedMetric, setExpandedMetric] = useState(null);

  if (!scorecard) return null;

  const {
    company,
    fiscal_year,
    overall_score = 80,
    risk_level = 'LOW_RISK',
    status_label = 'Pristine Quality',
    metrics = [],
    red_flags = [],
    positive_signals = [],
    summary = '',
  } = scorecard;

  // Determine stroke color and gradient based on risk level
  const getScoreTheme = (score) => {
    if (score >= 80) {
      return {
        color: '#059669', // emerald
        bg: '#ecfdf5',
        border: '#a7f3d0',
        label: 'Low Forensic Risk',
      };
    }
    if (score >= 55) {
      return {
        color: '#d97706', // amber
        bg: '#fffbeb',
        border: '#fde68a',
        label: 'Moderate Caution',
      };
    }
    return {
      color: '#dc2626', // crimson
      bg: '#fef2f2',
      border: '#fecaca',
      label: 'Elevated Risk',
    };
  };

  const theme = getScoreTheme(overall_score);

  // Radial Gauge SVG math
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (overall_score / 100) * circumference;

  return (
    <div className={`glass-panel forensic-radar-container ${skepticMode ? 'skeptic-active-panel' : ''}`}>
      {/* Header Bar */}
      <div className="forensic-radar-header">
        <div className="forensic-title-wrap">
          <div className="forensic-icon-box" style={{ background: theme.bg, color: theme.color, borderColor: theme.border }}>
            {overall_score >= 80 ? <ShieldCheck size={22} /> : <ShieldAlert size={22} />}
          </div>
          <div>
            <div className="forensic-title-row">
              <h3 className="forensic-title">Forensic Red Flag Radar</h3>
              {skepticMode && (
                <span className="skeptic-mode-pill">
                  <Zap size={12} />
                  <span>Skeptic Lens Active</span>
                </span>
              )}
            </div>
            <p className="forensic-subtitle">
              Deterministic accounting forensics & balance sheet solvency for <strong>{company}</strong> {fiscal_year ? `(FY${fiscal_year})` : ''}
            </p>
          </div>
        </div>

        <div className="forensic-provenance-tag">
          <Activity size={13} color="var(--accent-primary)" />
          <span>US-GAAP Machine Provenance</span>
        </div>
      </div>

      {/* Main Scorecard Section: Gauge + Diagnostic Cards */}
      <div className="forensic-body-grid">
        {/* Circular Gauge Card */}
        <div className="forensic-gauge-card">
          <div className="radial-gauge-wrapper">
            <svg className="radial-gauge-svg" width="136" height="136" viewBox="0 0 136 136">
              {/* Background Track */}
              <circle
                className="radial-gauge-track"
                cx="68"
                cy="68"
                r={radius}
                strokeWidth="10"
              />
              {/* Animated Progress Arc */}
              <circle
                className="radial-gauge-fill"
                cx="68"
                cy="68"
                r={radius}
                strokeWidth="10"
                stroke={theme.color}
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                transform="rotate(-90 68 68)"
              />
            </svg>
            <div className="gauge-center-content">
              <span className="gauge-number" style={{ color: theme.color }}>{overall_score}</span>
              <span className="gauge-max">/ 100</span>
            </div>
          </div>

          <div className="gauge-legend">
            <span className="gauge-status-badge" style={{ background: theme.bg, color: theme.color, borderColor: theme.border }}>
              {status_label}
            </span>
            <div className="gauge-sublabel">{theme.label}</div>
          </div>
        </div>

        {/* 3 Diagnostic Indicators */}
        <div className="forensic-metrics-col">
          {metrics.map((m, idx) => {
            const isPass = m.status === 'PASS';
            const isWarning = m.status === 'WARNING';
            const statusColor = isPass ? '#059669' : isWarning ? '#d97706' : '#dc2626';
            const statusBg = isPass ? '#ecfdf5' : isWarning ? '#fffbeb' : '#fef2f2';
            const statusBorder = isPass ? '#a7f3d0' : isWarning ? '#fde68a' : '#fecaca';
            const isExpanded = expandedMetric === m.metric_id;

            return (
              <div key={idx} className="forensic-metric-card">
                <div
                  className="metric-card-main"
                  onClick={() => setExpandedMetric(isExpanded ? null : m.metric_id)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="metric-header-row">
                    <div className="metric-info-left">
                      <span className="metric-name">{m.name}</span>
                      <span className="metric-val">{m.display_value}</span>
                    </div>

                    <div className="metric-status-group">
                      <span
                        className="metric-status-pill"
                        style={{ background: statusBg, color: statusColor, borderColor: statusBorder }}
                      >
                        {isPass ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                        <span>{m.status}</span>
                      </span>
                      <button type="button" className="metric-expand-btn" aria-label="Toggle Details">
                        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                    </div>
                  </div>

                  <p className="metric-desc">{m.description}</p>
                </div>

                {/* Collapsible Mathematical Provenance Drawer */}
                {isExpanded && (
                  <div className="metric-operands-drawer">
                    <div className="formula-box">
                      <span className="formula-label">Formula:</span>
                      <code>{m.formula}</code>
                    </div>

                    {m.operands && Object.keys(m.operands).length > 0 && (
                      <div className="operands-grid">
                        {Object.entries(m.operands).map(([key, op]) => (
                          <div key={key} className="operand-item">
                            <span className="operand-key">{key.replace(/_/g, ' ')}:</span>
                            <span className="operand-val">
                              {op.value !== null && op.value !== undefined
                                ? `$${(op.value / 1e9).toFixed(2)}B`
                                : 'N/A'}
                            </span>
                            {op.tag && <span className="operand-tag">{op.tag}</span>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Red Flags & Positive Signals Summary Banner */}
      {(red_flags.length > 0 || positive_signals.length > 0) && (
        <div className="forensic-signals-banner">
          {red_flags.length > 0 && (
            <div className="signal-block warning-signals">
              <div className="signal-block-title">
                <AlertTriangle size={14} color="#d97706" />
                <span>Forensic Watch Items ({red_flags.length})</span>
              </div>
              <ul className="signals-list">
                {red_flags.map((flag, fIdx) => (
                  <li key={fIdx} className="signal-item warning-item">{flag}</li>
                ))}
              </ul>
            </div>
          )}

          {positive_signals.length > 0 && (
            <div className="signal-block positive-signals">
              <div className="signal-block-title">
                <CheckCircle2 size={14} color="#059669" />
                <span>Accounting Strengths ({positive_signals.length})</span>
              </div>
              <ul className="signals-list">
                {positive_signals.map((sig, sIdx) => (
                  <li key={sIdx} className="signal-item positive-item">{sig}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Forensic Verdict Quote */}
      {summary && (
        <div className="forensic-verdict-box">
          <Info size={15} color="var(--accent-primary)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <p className="verdict-text">{summary}</p>
        </div>
      )}
    </div>
  );
}
