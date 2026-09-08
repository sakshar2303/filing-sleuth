import React from 'react';
import {
  FileText,
  AlertTriangle,
  Table,
  Calculator,
  ShieldCheck,
  ExternalLink,
  Database,
  Quote,
  CheckCircle2,
} from 'lucide-react';

export default function ResultReport({ result, onSelectCitation }) {
  if (!result) return null;

  const { synthesis_report, computations, plan, all_quotes_verified } = result;
  const citations = synthesis_report?.citations || [];
  const calendarWarnings = (synthesis_report?.caveats_and_notes || []).filter(n =>
    n.toLowerCase().includes('calendar') || n.toLowerCase().includes('fiscal') || n.toLowerCase().includes('month') || n.toLowerCase().includes('mismatch')
  );

  // Parse markdown table rows if present
  const tableMd = synthesis_report?.comparison_table_markdown || '';
  const parseMarkdownTable = (md) => {
    const lines = md.trim().split('\n').filter(l => l.includes('|'));
    if (lines.length < 2) return null;

    const headers = lines[0].split('|').map(s => s.trim()).filter(Boolean);
    const rows = lines.slice(2).map(l => l.split('|').map(s => s.trim()).filter(Boolean));
    return { headers, rows };
  };

  const parsedTable = parseMarkdownTable(tableMd);

  // Replace citation markers like [1], [2] in text with clickable badges
  const renderTextWithCitations = (text) => {
    if (!text) return null;
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, i) => {
      const match = part.match(/\[(\d+)\]/);
      if (match) {
        const num = match[1];
        const cit = citations.find(c => c.citation_id === `[${num}]`);
        return (
          <button
            key={i}
            type="button"
            onClick={() => cit && onSelectCitation(cit)}
            style={{
              background: '#f0fdfa',
              border: '1px solid #99f6e4',
              color: '#0f766e',
              borderRadius: '4px',
              padding: '0.1rem 0.4rem',
              fontSize: '0.8rem',
              fontWeight: 800,
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer',
              margin: '0 0.15rem',
              display: 'inline-flex',
              alignItems: 'center',
              verticalAlign: 'baseline',
            }}
            title={`View Citation [${num}]`}
          >
            [{num}]
          </button>
        );
      }
      return part;
    });
  };

  return (
    <div className="results-container">
      {/* 1. Executive Summary */}
      <div className="glass-panel summary-card">
        <div className="summary-title">
          <FileText size={20} color="#0f766e" />
          <span>Executive Briefing</span>
          {all_quotes_verified && (
            <span className="badge badge-verified" style={{ marginLeft: 'auto' }}>
              <CheckCircle2 size={13} /> Zero Hallucination Verified
            </span>
          )}
        </div>
        <p className="summary-text">
          {renderTextWithCitations(synthesis_report?.executive_summary || 'No summary generated.')}
        </p>
      </div>

      {/* 2. Calendar Mismatch Warning (if Apple Sept vs MSFT June etc.) */}
      {calendarWarnings.length > 0 && (
        <div className="calendar-alert">
          <AlertTriangle size={22} color="#d97706" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <div className="calendar-alert-title">Fiscal Calendar Misalignment Detected</div>
            <div className="calendar-alert-desc">
              {calendarWarnings.map((w, idx) => (
                <div key={idx}>{w}</div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 3. Comparison Matrix Table */}
      {parsedTable && (
        <div className="glass-panel table-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Table size={18} color="#0284c7" />
            <h3 style={{ fontSize: '1.05rem', color: '#0f172a' }}>Multi-Company Alignment Matrix</h3>
          </div>
          <table className="markdown-table">
            <thead>
              <tr>
                {parsedTable.headers.map((h, i) => (
                  <th key={i}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {parsedTable.rows.map((row, rIdx) => (
                <tr key={rIdx}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} style={{ fontWeight: cIdx === 0 ? 600 : 400 }}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 4. Computed Ratios & Spread Deltas */}
      {computations && computations.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <Calculator size={18} color="#0f766e" />
            <h3 style={{ fontSize: '1.05rem', color: '#0f172a' }}>Deterministic Computations</h3>
          </div>
          <div className="computations-grid">
            {computations.map((c, i) => (
              <div key={i} className="glass-panel comp-card">
                <div className="comp-header">
                  <span className="comp-label">{c.company} (FY{c.fiscal_year})</span>
                  <span className="badge badge-xbrl">Ratio</span>
                </div>
                <div className="comp-value">{c.result_formatted}</div>
                <div className="comp-formula">
                  {c.numerator_label} (${(c.numerator_value / 1e9).toFixed(1)}B) / {c.denominator_label} (${(c.denominator_value / 1e9).toFixed(1)}B)
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '0.25rem', lineHeight: 1.5 }}>
                  {c.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. Grounded Citations & Audit Footnotes */}
      {citations.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <ShieldCheck size={18} color="#0f766e" />
            <h3 style={{ fontSize: '1.05rem', color: '#0f172a' }}>
              SEC Provenance & Grounded Citations ({citations.length})
            </h3>
          </div>
          <div className="citations-grid">
            {citations.map((cit, idx) => (
              <div
                key={idx}
                className="glass-panel citation-card"
                onClick={() => onSelectCitation(cit)}
              >
                <div className="citation-top">
                  <span className="citation-num">{cit.citation_id}</span>
                  {cit.source_type === 'XBRL' ? (
                    <span className="badge badge-xbrl"><Database size={11} /> XBRL Fact</span>
                  ) : (
                    <span className="badge badge-verified"><ShieldCheck size={11} /> 10-K Text</span>
                  )}
                </div>

                <div className="citation-company">{cit.company}</div>

                {cit.exact_quote ? (
                  <div className="citation-quote">
                    "{cit.exact_quote.length > 130 ? cit.exact_quote.slice(0, 130) + '...' : cit.exact_quote}"
                  </div>
                ) : cit.xbrl_tag ? (
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#0284c7', fontWeight: 600 }}>
                    {cit.xbrl_tag}
                  </div>
                ) : null}

                <div className="citation-meta">
                  <span>{cit.item_section || 'SEC 10-K'}</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', color: '#0f766e', fontWeight: 700 }}>
                    Inspect <ExternalLink size={12} />
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
