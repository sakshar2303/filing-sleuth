import React, { useState } from 'react';
import { BarChart3, TrendingUp, HelpCircle, Layers, Sparkles } from 'lucide-react';
import TiltCard from './TiltCard';

export default function FinancialChart({ result }) {
  if (!result) return null;

  const { extracted_facts = [], computations = {} } = result;
  const [hoveredPoint, setHoveredPoint] = useState(null);

  // 1. Check for multi-company comparison data
  const ratios = computations?.ratios || [];
  const spread = computations?.comparison_spread;

  // Distinct companies in extracted facts
  const companies = Array.from(new Set(extracted_facts.map((f) => f.company || f.ticker)));
  const isComparison = ratios.length >= 2 || (companies.length >= 2 && extracted_facts.length >= 2);

  // 2. Check for multi-year trend data for a single company
  const factsWithYears = extracted_facts.filter((f) => f.fiscal_year && typeof f.value === 'number');
  const distinctYears = Array.from(new Set(factsWithYears.map((f) => f.fiscal_year))).sort((a, b) => a - b);
  const isTrend = distinctYears.length >= 2;

  if (!isComparison && !isTrend) {
    return null; // No multi-point quantitative data to graph
  }

  // Format big currency / number values
  const formatValue = (val, unit = 'USD') => {
    if (val === null || val === undefined) return 'N/A';
    if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
    if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
    if (Math.abs(val) >= 1e3) return `$${(val / 1e3).toFixed(1)}K`;
    return `$${val.toLocaleString()}`;
  };

  return (
    <TiltCard className="financial-chart-card" maxTilt={3} scale={1.008}>

      <div className="chart-header">
        <div className="chart-title-group">
          <div className="chart-badge">
            {isComparison ? <BarChart3 size={15} /> : <TrendingUp size={15} />}
            <span>{isComparison ? 'Peer Comparison Model' : 'Longitudinal Trend Analysis'}</span>
          </div>
          <h4 className="chart-heading">
            {isComparison
              ? 'Cross-Company Margin & Allocation Benchmarking'
              : `Multi-Year Performance Trend (${distinctYears.join(' → ')})`}
          </h4>
        </div>

        {spread && (
          <div className="chart-spread-badge">
            <span className="spread-label">Spread:</span>
            <span className="spread-value">{spread.spread_bps > 0 ? `+${spread.spread_bps}` : spread.spread_bps} bps</span>
          </div>
        )}
      </div>

      {/* --- RENDER COMPARISON BAR CHART --- */}
      {isComparison && ratios.length >= 2 && (
        <div className="comparison-bar-container">
          <div className="bars-wrapper">
            {ratios.map((r, idx) => {
              const pct = typeof r.value === 'number' ? r.value * 100 : parseFloat(r.percentage_str) || 0;
              const maxVal = Math.max(...ratios.map((item) => (typeof item.value === 'number' ? item.value * 100 : parseFloat(item.percentage_str) || 0)), 1);
              const barWidthPct = Math.min(Math.max((pct / maxVal) * 88, 12), 98);
              const isFirst = idx === 0;

              return (
                <div key={idx} className="comparison-bar-row">
                  <div className="bar-label-col">
                    <span className="bar-company-name">{r.name || `Peer ${idx + 1}`}</span>
                    <span className="bar-pct-tag">{r.percentage_str || `${pct.toFixed(2)}%`}</span>
                  </div>
                  <div className="bar-track-col">
                    <div
                      className="bar-fill"
                      style={{
                        width: `${barWidthPct}%`,
                        backgroundColor: isFirst ? 'var(--accent-primary)' : 'var(--cyan)',
                      }}
                    >
                      <span className="bar-inner-text">{r.percentage_str || `${pct.toFixed(2)}%`}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {spread && (
            <div className="chart-footer-note">
              <Sparkles size={14} color="var(--accent-primary)" />
              <span>{spread.summary} (Calculated deterministically via XBRL ground truth)</span>
            </div>
          )}
        </div>
      )}

      {/* --- RENDER MULTI-YEAR TREND SVG CHART --- */}
      {isTrend && (!isComparison || ratios.length < 2) && (
        <div className="trend-svg-container">
          {(() => {
            // Group facts by year
            const yearMap = {};
            factsWithYears.forEach((f) => {
              if (!yearMap[f.fiscal_year]) yearMap[f.fiscal_year] = f;
            });
            const sortedFacts = distinctYears.map((y) => yearMap[y]).filter(Boolean);

            if (sortedFacts.length < 2) return null;

            const values = sortedFacts.map((f) => f.value);
            const minVal = Math.min(...values);
            const maxVal = Math.max(...values);
            const valRange = maxVal - minVal || 1;

            const svgWidth = 600;
            const svgHeight = 180;
            const padding = { top: 30, right: 40, bottom: 40, left: 70 };
            const chartW = svgWidth - padding.left - padding.right;
            const chartH = svgHeight - padding.top - padding.bottom;

            const points = sortedFacts.map((f, i) => {
              const x = padding.left + (i / (sortedFacts.length - 1)) * chartW;
              const y = padding.top + chartH - ((f.value - minVal) / valRange) * chartH;
              return { x, y, fact: f };
            });

            const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
            const areaD = `${pathD} L ${points[points.length - 1].x} ${padding.top + chartH} L ${points[0].x} ${padding.top + chartH} Z`;

            return (
              <div style={{ position: 'relative' }}>
                <svg
                  viewBox={`0 0 ${svgWidth} ${svgHeight}`}
                  className="trend-svg"
                  preserveAspectRatio="xMidYMid meet"
                >
                  <defs>
                    <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--accent-primary)" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="var(--accent-primary)" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Horizontal Gridlines */}
                  {[0, 0.5, 1].map((ratio, idx) => {
                    const y = padding.top + chartH * (1 - ratio);
                    const labelVal = minVal + valRange * ratio;
                    return (
                      <g key={idx}>
                        <line
                          x1={padding.left}
                          y1={y}
                          x2={padding.left + chartW}
                          y2={y}
                          stroke="var(--border-subtle)"
                          strokeDasharray="4 4"
                        />
                        <text
                          x={padding.left - 10}
                          y={y + 4}
                          fill="var(--text-muted)"
                          fontSize="10"
                          textAnchor="end"
                          fontFamily="var(--font-mono)"
                        >
                          {formatValue(labelVal)}
                        </text>
                      </g>
                    );
                  })}

                  {/* Area fill */}
                  <path d={areaD} fill="url(#areaGradient)" />

                  {/* Trend Line */}
                  <path
                    d={pathD}
                    fill="none"
                    stroke="var(--accent-primary)"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />

                  {/* Points & Labels */}
                  {points.map((p, i) => (
                    <g key={i} className="chart-point-group">
                      <circle
                        cx={p.x}
                        cy={p.y}
                        r="6"
                        fill="#ffffff"
                        stroke="var(--accent-primary)"
                        strokeWidth="3"
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={() => setHoveredPoint(p)}
                        onMouseLeave={() => setHoveredPoint(null)}
                      />
                      {/* Year Label below axis */}
                      <text
                        x={p.x}
                        y={svgHeight - 12}
                        fill="var(--text-secondary)"
                        fontSize="12"
                        fontWeight="600"
                        textAnchor="middle"
                        fontFamily="var(--font-mono)"
                      >
                        FY{p.fact.fiscal_year}
                      </text>
                      {/* Value callout above point */}
                      <text
                        x={p.x}
                        y={p.y - 12}
                        fill="var(--accent-primary)"
                        fontSize="11"
                        fontWeight="700"
                        textAnchor="middle"
                        fontFamily="var(--font-mono)"
                      >
                        {formatValue(p.fact.value)}
                      </text>
                    </g>
                  ))}
                </svg>

                {/* Hover Tooltip */}
                {hoveredPoint && (
                  <div
                    className="chart-tooltip"
                    style={{
                      left: `${(hoveredPoint.x / svgWidth) * 100}%`,
                      top: `${hoveredPoint.y - 10}px`,
                    }}
                  >
                    <div style={{ fontWeight: 700 }}>
                      {hoveredPoint.fact.company} (FY{hoveredPoint.fact.fiscal_year})
                    </div>
                    <div>Concept: <code>{hoveredPoint.fact.metric}</code></div>
                    <div>Amount: {formatValue(hoveredPoint.fact.value)} {hoveredPoint.fact.unit}</div>
                    {hoveredPoint.fact.accession_number && (
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        SEC Acc: {hoveredPoint.fact.accession_number}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}
    </TiltCard>
  );
}

