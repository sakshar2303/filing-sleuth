import React, { useState } from 'react';
import { Terminal, ChevronDown, ChevronUp, CheckCircle2, CircleDot } from 'lucide-react';

export default function ReasoningTrace({ trace, isLive }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [expandedStep, setExpandedStep] = useState(null);

  if (!trace || trace.length === 0) return null;

  const toggleStepData = (idx) => {
    setExpandedStep(expandedStep === idx ? null : idx);
  };

  return (
    <div className="glass-panel trace-panel">
      <div className="trace-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="trace-title">
          <Terminal size={18} color="#0f766e" />
          <span>Agent Execution Trace ({trace.length} steps)</span>
          {isLive && (
            <span className="badge badge-verified" style={{ marginLeft: '0.5rem', animation: 'pulse-dot 1.5s infinite' }}>
              LIVE STREAMING
            </span>
          )}
        </div>
        <button
          type="button"
          style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}
        >
          {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
      </div>

      {isExpanded && (
        <div className="trace-timeline">
          {trace.map((step, idx) => {
            const isComplete = step.step_name === 'COMPLETE';
            const hasData = step.data && Object.keys(step.data).length > 0;
            const isDataOpen = expandedStep === idx;

            return (
              <div
                key={idx}
                className={`trace-item ${isComplete ? 'complete' : ''}`}
                style={{ cursor: hasData ? 'pointer' : 'default' }}
                onClick={() => hasData && toggleStepData(idx)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className="trace-step-tag">[{step.step_name}]</span>
                  <span className="trace-step-desc">{step.description}</span>
                  {hasData && (
                    <span style={{ fontSize: '0.7rem', color: '#0f766e', fontWeight: 600, textDecoration: 'underline', marginLeft: 'auto' }}>
                      {isDataOpen ? 'Hide Payload' : 'View Payload'}
                    </span>
                  )}
                </div>

                {isDataOpen && hasData && (
                  <pre
                    style={{
                      background: '#f8fafc',
                      padding: '0.6rem 0.8rem',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      fontFamily: 'var(--font-mono)',
                      color: '#0f172a',
                      marginTop: '0.4rem',
                      overflowX: 'auto',
                      border: '1px solid #e2e8f0',
                    }}
                  >
                    {JSON.stringify(step.data, null, 2)}
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
