import React from 'react';
import {
  FileText,
  AlertTriangle,
  Table,
  Calculator,
  ShieldCheck,
  ExternalLink,
  Database,
  CheckCircle2,
  TrendingUp,
  DollarSign,
  Percent,
  Activity,
  ListChecks,
  Sparkles,
} from 'lucide-react';
import FinancialChart from './FinancialChart';
import ExportToolbar from './ExportToolbar';
import ForensicRadar from './ForensicRadar';

export default function ResultReport({ result, onSelectCitation }) {
  if (!result) return null;

  const {
    synthesis_report,
    computations = [],
    plan,
    all_quotes_verified,
    forensic_scorecard,
    chart_data,
    skeptic_mode,
  } = result;

  const citations = synthesis_report?.citations || [];
  const calendarWarnings = (synthesis_report?.caveats_and_notes || []).filter((n) =>
    n.toLowerCase().includes('calendar') ||
    n.toLowerCase().includes('fiscal') ||
    n.toLowerCase().includes('month') ||
    n.toLowerCase().includes('mismatch')
  );

  const summaryKpis = chart_data?.summary_kpis || {};

  // Parse markdown table rows if present
  const tableMd = synthesis_report?.comparison_table_markdown || '';
  const parseMarkdownTable = (md) => {
    if (!md) return null;
    const lines = md.trim().split('\n').filter((l) => l.includes('|'));
    if (lines.length < 2) return null;

    const headers = lines[0].split('|').map((s) => s.trim()).filter(Boolean);
    const rows = lines.slice(2).map((l) => l.split('|').map((s) => s.trim()).filter(Boolean));
    return { headers, rows };
  };

  const parsedTable = parseMarkdownTable(tableMd);

  // Replace citation markers like [1], [2] in text with clickable badges
  const renderTextWithCitations = (text) => {
    if (!text) return null;

    // Normalize skeptic prefix if preceding header
    const cleanText = text.replace(/\[FORENSIC SKEPTIC MEMO\]\s*###/g, '### [Forensic Skeptic Memo]');

    const blocks = cleanText.split('\n\n');

    return (
      <div className="report-memo-body">
        {blocks.map((block, bIdx) => {
          const trimmed = block.trim();
          if (!trimmed) return null;

          const lines = trimmed.split('\n');
          return (
            <div key={bIdx} className="memo-block">
              {lines.map((line, lIdx) => {
                const lineTrimmed = line.trim();
                if (!lineTrimmed) return null;

                if (lineTrimmed.startsWith('### ')) {
                  return (
                    <h4 key={lIdx} className="memo-subheading">
                      {lineTrimmed.replace('### ', '')}
                    </h4>
                  );
                }

                const parts = lineTrimmed.split(/(\[\d+\]|\*\*[^*]+\*\*)/g);
                return (
                  <p key={lIdx} className="memo-paragraph">
                    {parts.map((part, i) => {
                      const citMatch = part.match(/\[(\d+)\]/);
                      if (citMatch) {
                        const num = citMatch[1];
                        const cit = citations.find((c) => c.citation_id === `[${num}]`);
                        return (
                          <button
                            key={i}
                            type="button"
                            onClick={() => cit && onSelectCitation(cit)}
                            className="inline-citation-badge"
                            title={`View Source Citation [${num}]`}
                          >
                            [{num}]
                          </button>
                        );
                      }

                      if (part.startsWith('**') && part.endsWith('**')) {
                        return (
                          <strong key={i} className="memo-strong">
                            {part.slice(2, -2)}
                          </strong>
                        );
                      }

                      return part;
                    })}
                  </p>
                );
              })}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="results-container">
      {/* 0. Print Letterhead (Only visible during window.print) */}
      <div className="print-only-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '2px solid #0f766e', paddingBottom: '0.75rem', marginBottom: '1.5rem' }}>
          <div>
            <h1 style={{ fontSize: '1.6rem', color: '#0f172a', fontWeight: 800 }}>FILING SLEUTH</h1>
            <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Institutional SEC EDGAR Financial Research Dossier</div>
          </div>
          <div style={{ textAlign: 'right', fontSize: '0.8rem', color: '#64748b' }}>
            <div>Date: {new Date().toLocaleDateString()}</div>
            <div>Status: Grounded XBRL & Verified Citations</div>
          </div>
        </div>
      </div>

      {/* 1. EXECUTIVE KPI STRIP (Wall Street Quick-Look) */}
      {summaryKpis && summaryKpis.latest_revenue_formatted && (
        <div className="executive-kpi-strip">
          <div className="kpi-metric-card">
            <div className="kpi-header">
              <span className="kpi-icon-pill" style={{ background: '#ecfdf5', color: '#059669' }}>
                <DollarSign size={14} />
              </span>
              <span className="kpi-label">Total Revenue</span>
            </div>
            <div className="kpi-value">{summaryKpis.latest_revenue_formatted}</div>
            <div className="kpi-subtext">
              FY{summaryKpis.latest_fiscal_year} Audited 10-K
            </div>
          </div>

          <div className="kpi-metric-card">
            <div className="kpi-header">
              <span className="kpi-icon-pill" style={{ background: '#ecfeff', color: '#0891b2' }}>
                <TrendingUp size={14} />
              </span>
              <span className="kpi-label">Net Income</span>
            </div>
            <div className="kpi-value">{summaryKpis.latest_net_income_formatted}</div>
            <div className="kpi-subtext">
              {summaryKpis.latest_net_margin !== null ? `Net Margin: ${summaryKpis.latest_net_margin}%` : 'GAAP Net Earnings'}
            </div>
          </div>

          <div className="kpi-metric-card">
            <div className="kpi-header">
              <span className="kpi-icon-pill" style={{ background: '#f0fdf4', color: '#16a34a' }}>
                <Percent size={14} />
              </span>
              <span className="kpi-label">Operating Margin</span>
            </div>
            <div className="kpi-value">
              {summaryKpis.latest_operating_margin !== null ? `${summaryKpis.latest_operating_margin}%` : 'N/A'}
            </div>
            <div className="kpi-subtext">
              Operating Efficiency
            </div>
          </div>

          <div className="kpi-metric-card">
            <div className="kpi-header">
              <span className="kpi-icon-pill" style={{ background: '#faf5ff', color: '#9333ea' }}>
                <Activity size={14} />
              </span>
              <span className="kpi-label">1-Yr YoY Growth</span>
            </div>
            <div className="kpi-value" style={{ color: summaryKpis.yoy_revenue_growth_pct >= 0 ? '#059669' : '#e11d48' }}>
              {summaryKpis.yoy_revenue_growth_pct !== null
                ? `${summaryKpis.yoy_revenue_growth_pct >= 0 ? '+' : ''}${summaryKpis.yoy_revenue_growth_pct}%`
                : '—'}
            </div>
            <div className="kpi-subtext">
              {summaryKpis.three_year_cagr_revenue_pct !== null
                ? `3-Yr CAGR: ${summaryKpis.three_year_cagr_revenue_pct > 0 ? '+' : ''}${summaryKpis.three_year_cagr_revenue_pct}%`
                : 'Annualized Momentum'}
            </div>
          </div>

          {forensic_scorecard && (
            <div className="kpi-metric-card">
              <div className="kpi-header">
                <span className="kpi-icon-pill" style={{ background: '#fef3c7', color: '#b45309' }}>
                  <ShieldCheck size={14} />
                </span>
                <span className="kpi-label">Forensic Score</span>
              </div>
              <div className="kpi-value" style={{ color: forensic_scorecard.risk_level === 'LOW_RISK' ? '#059669' : forensic_scorecard.risk_level === 'GRAY_ZONE' ? '#d97706' : '#e11d48' }}>
                {forensic_scorecard.overall_score}/100
              </div>
              <div className="kpi-subtext" style={{ textTransform: 'capitalize' }}>
                {forensic_scorecard.status_label}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 2. INTERACTIVE FINANCIAL CHARTING SUITE */}
      <FinancialChart result={result} />

      {/* 3. EXECUTIVE BRIEFING & RESEARCH MEMO */}
      <div className="glass-panel summary-card">
        <div className="summary-title" style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FileText size={20} color="#0f766e" />
            <span>Institutional Research Memo</span>
          </div>
          {all_quotes_verified && (
            <span className="badge badge-verified">
              <CheckCircle2 size={13} /> Zero Hallucination Verified
            </span>
          )}
          {skeptic_mode && (
            <span className="badge badge-skeptic" style={{ background: '#fef3c7', color: '#b45309', border: '1px solid #fde68a' }}>
              Forensic Skeptic Mode Active
            </span>
          )}

          {/* Export Actions Toolbar */}
          <div style={{ marginLeft: 'auto' }}>
            <ExportToolbar result={result} />
          </div>
        </div>

        {renderTextWithCitations(synthesis_report?.executive_summary || 'No report generated.')}
      </div>

      {/* 4. KEY ANALYTICAL FINDINGS & STRATEGIC DRIVERS */}
      {synthesis_report?.key_findings && synthesis_report.key_findings.length > 0 && (
        <div className="glass-panel key-findings-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <ListChecks size={18} color="#0f766e" />
            <h3 style={{ fontSize: '1.1rem', color: '#0f172a', fontWeight: 700 }}>
              Key Analytical Findings & Strategic Drivers ({synthesis_report.key_findings.length})
            </h3>
          </div>
          <div className="key-findings-grid">
            {synthesis_report.key_findings.map((finding, idx) => (
              <div key={idx} className="finding-row-item">
                <div className="finding-index-bullet">{idx + 1}</div>
                <div className="finding-text-col">
                  {renderTextWithCitations(finding)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. AUTOMATED FORENSIC RED FLAG RADAR */}
      <ForensicRadar scorecard={forensic_scorecard} skepticMode={skeptic_mode} />

      {/* 6. FISCAL CALENDAR MISMATCH WARNING */}
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

      {/* 7. COMPREHENSIVE MULTI-YEAR FINANCIAL STATEMENT BREAKDOWN */}
      {parsedTable && (
        <div className="glass-panel table-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Table size={18} color="#0284c7" />
            <h3 style={{ fontSize: '1.1rem', color: '#0f172a', fontWeight: 700 }}>
              Multi-Year Financial Statement Breakdown
            </h3>
          </div>
          <div className="table-scroll-wrapper">
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
                    {row.map((cell, cIdx) => {
                      const cleanCell = cell.replace(/\*\*/g, '').trim();
                      const isBold = cell.includes('**') || cIdx === 0;
                      return (
                        <td
                          key={cIdx}
                          style={{
                            fontWeight: isBold ? 700 : 400,
                            color: isBold && cIdx === 0 ? 'var(--text-primary)' : 'inherit',
                            textAlign: cIdx === 0 ? 'left' : 'right',
                            fontFamily: cIdx === 0 ? 'inherit' : 'var(--font-mono)',
                          }}
                        >
                          {cleanCell}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 8. DETERMINISTIC COMPUTATIONS & MARGIN DERIVATIONS */}
      {computations && computations.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <Calculator size={18} color="#0f766e" />
            <h3 style={{ fontSize: '1.1rem', color: '#0f172a', fontWeight: 700 }}>
              Deterministic Computations & Ratios ({computations.length})
            </h3>
          </div>
          <div className="computations-grid">
            {computations.slice(0, 8).map((c, i) => (
              <div key={i} className="glass-panel comp-card">
                <div className="comp-header">
                  <span className="comp-label">{c.company} (FY{c.fiscal_year})</span>
                  <span className="badge badge-xbrl">{c.metric_label || c.type || 'Ratio'}</span>
                </div>
                <div className="comp-value">{c.result_formatted}</div>
                {c.formula && (
                  <div className="comp-formula">
                    <code>{c.formula}</code>
                  </div>
                )}
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '0.35rem', lineHeight: 1.5 }}>
                  {c.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 9. GROUNDED CITATIONS & SEC PROVENANCE DOSSIER */}
      {citations.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <ShieldCheck size={18} color="#0f766e" />
            <h3 style={{ fontSize: '1.1rem', color: '#0f172a', fontWeight: 700 }}>
              SEC EDGAR Grounded Provenance & Citations ({citations.length})
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
                    <span className="badge badge-xbrl"><Database size={11} /> XBRL Tag</span>
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
