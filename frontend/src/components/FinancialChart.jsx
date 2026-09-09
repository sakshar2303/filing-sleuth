import React, { useState } from 'react';
import {
  BarChart3,
  TrendingUp,
  Percent,
  Wallet,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  Layers,
  ChevronRight,
} from 'lucide-react';
import TiltCard from './TiltCard';

export default function FinancialChart({ result }) {
  if (!result) return null;

  const { chart_data, extracted_facts = [], computations = [] } = result;

  // 1. Determine available data sources
  const series = chart_data?.series || [];
  const years = chart_data?.years || [];
  const summaryKpis = chart_data?.summary_kpis || {};
  const companyName = chart_data?.company || 'Target Registrant';

  // Multi-company peer comparisons from computations
  const ratios = Array.isArray(computations)
    ? computations.filter((c) => c.type === 'RATIO_PERCENT' || c.computation_type === 'MARGIN_RATIO')
    : computations?.ratios || [];
  const spread = computations?.comparison_spread;

  // Fallback to legacy extracted_facts if chart_data series is not present
  const factsWithYears = extracted_facts.filter((f) => f.fiscal_year && typeof f.value === 'number');
  const distinctYears = Array.from(new Set(factsWithYears.map((f) => f.fiscal_year))).sort((a, b) => a - b);

  const hasSeriesData = series.length >= 2;
  const isComparison = ratios.length >= 2;
  const hasLegacyTrend = distinctYears.length >= 2;

  if (!hasSeriesData && !isComparison && !hasLegacyTrend) {
    return null;
  }

  // Active Tab State
  const [activeTab, setActiveTab] = useState(hasSeriesData ? 'revenue_earnings' : isComparison ? 'peer' : 'revenue_earnings');
  const [hoveredItem, setHoveredItem] = useState(null);

  // Format Currency
  const formatCurrency = (val) => {
    if (val === null || val === undefined) return 'N/A';
    const absVal = Math.abs(val);
    const sign = val < 0 ? '-' : '';
    if (absVal >= 1e12) return `${sign}$${(absVal / 1e12).toFixed(2)}T`;
    if (absVal >= 1e9) return `${sign}$${(absVal / 1e9).toFixed(2)}B`;
    if (absVal >= 1e6) return `${sign}$${(absVal / 1e6).toFixed(2)}M`;
    if (absVal >= 1e3) return `${sign}$${(absVal / 1e3).toFixed(1)}K`;
    return `${sign}$${val.toLocaleString()}`;
  };

  return (
    <TiltCard className="financial-chart-card" maxTilt={2} scale={1.004}>
      {/* Chart Header & Navigation Tabs */}
      <div className="chart-header-bar">
        <div className="chart-title-group">
          <div className="chart-badge">
            <BarChart3 size={15} color="var(--accent-primary)" />
            <span>Interactive Financial Intelligence</span>
          </div>
          <h3 className="chart-heading">
            {companyName} Multi-Year Performance & Margin Trajectory
          </h3>
        </div>

        {/* Tab Controls */}
        <div className="chart-tabs-dock">
          {hasSeriesData && (
            <>
              <button
                type="button"
                className={`chart-tab-btn ${activeTab === 'revenue_earnings' ? 'active' : ''}`}
                onClick={() => setActiveTab('revenue_earnings')}
              >
                <TrendingUp size={13} />
                <span>Revenue & Earnings</span>
              </button>
              <button
                type="button"
                className={`chart-tab-btn ${activeTab === 'margins' ? 'active' : ''}`}
                onClick={() => setActiveTab('margins')}
              >
                <Percent size={13} />
                <span>Profit Margins</span>
              </button>
              <button
                type="button"
                className={`chart-tab-btn ${activeTab === 'cash_flow' ? 'active' : ''}`}
                onClick={() => setActiveTab('cash_flow')}
              >
                <Wallet size={13} />
                <span>Cash Flow & FCF</span>
              </button>
            </>
          )}

          {isComparison && (
            <button
              type="button"
              className={`chart-tab-btn ${activeTab === 'peer' ? 'active' : ''}`}
              onClick={() => setActiveTab('peer')}
            >
              <Layers size={13} />
              <span>Peer Benchmark</span>
            </button>
          )}
        </div>
      </div>

      {/* ── TAB 1: REVENUE & NET INCOME TRAJECTORY (DUAL BARS) ── */}
      {activeTab === 'revenue_earnings' && hasSeriesData && (
        <div className="chart-body-container">
          <div className="chart-legend-row">
            <div className="legend-item">
              <span className="legend-color-dot" style={{ backgroundColor: '#0f766e' }} />
              <span>Total Revenue ($B)</span>
            </div>
            <div className="legend-item">
              <span className="legend-color-dot" style={{ backgroundColor: '#06b6d4' }} />
              <span>Net Income ($B)</span>
            </div>
            {summaryKpis?.three_year_cagr_revenue_pct !== null && (
              <div className="cagr-pill-badge">
                <Sparkles size={13} />
                <span>3-Yr Top-Line CAGR: {summaryKpis.three_year_cagr_revenue_pct > 0 ? `+${summaryKpis.three_year_cagr_revenue_pct}` : summaryKpis.three_year_cagr_revenue_pct}%</span>
              </div>
            )}
          </div>

          {/* SVG Dual Bar Visualization */}
          {(() => {
            const maxRev = Math.max(...series.map((s) => s.revenue || 0), 1);
            const svgWidth = 720;
            const svgHeight = 260;
            const padding = { top: 35, right: 30, bottom: 45, left: 65 };
            const chartW = svgWidth - padding.left - padding.right;
            const chartH = svgHeight - padding.top - padding.bottom;

            const groupWidth = chartW / series.length;
            const barW = Math.min(groupWidth * 0.32, 42);

            return (
              <div style={{ position: 'relative' }}>
                <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="financial-svg-canvas">
                  <defs>
                    <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0f766e" stopOpacity="0.95" />
                      <stop offset="100%" stopColor="#115e59" stopOpacity="0.75" />
                    </linearGradient>
                    <linearGradient id="netGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.95" />
                      <stop offset="100%" stopColor="#0891b2" stopOpacity="0.75" />
                    </linearGradient>
                  </defs>

                  {/* Gridlines */}
                  {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
                    const y = padding.top + chartH * (1 - ratio);
                    const labelVal = maxRev * ratio;
                    return (
                      <g key={idx}>
                        <line
                          x1={padding.left}
                          y1={y}
                          x2={padding.left + chartW}
                          y2={y}
                          stroke="var(--border-subtle)"
                          strokeDasharray="3 3"
                        />
                        <text
                          x={padding.left - 8}
                          y={y + 4}
                          fill="var(--text-muted)"
                          fontSize="10"
                          textAnchor="end"
                          fontFamily="var(--font-mono)"
                        >
                          {formatCurrency(labelVal)}
                        </text>
                      </g>
                    );
                  })}

                  {/* Dual Bars per Year */}
                  {series.map((item, idx) => {
                    const groupX = padding.left + idx * groupWidth;
                    const centerX = groupX + groupWidth / 2;

                    const revH = item.revenue ? Math.max((item.revenue / maxRev) * chartH, 4) : 0;
                    const netH = item.net_income ? Math.max((Math.max(item.net_income, 0) / maxRev) * chartH, 2) : 0;

                    const revX = centerX - barW - 3;
                    const netX = centerX + 3;

                    const revY = padding.top + chartH - revH;
                    const netY = padding.top + chartH - netH;

                    return (
                      <g
                        key={item.fiscal_year}
                        className="chart-bar-group"
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={() => setHoveredItem({ type: 'rev_net', item, x: centerX, y: revY })}
                        onMouseLeave={() => setHoveredItem(null)}
                      >
                        {/* YoY Growth pill above revenue bar */}
                        {item.yoy_revenue_growth_pct !== null && (
                          <g>
                            <rect
                              x={centerX - 30}
                              y={Math.max(revY - 24, 8)}
                              width="60"
                              height="18"
                              rx="9"
                              fill={item.yoy_revenue_growth_pct >= 0 ? '#ecfdf5' : '#fff1f2'}
                              stroke={item.yoy_revenue_growth_pct >= 0 ? '#10b981' : '#f43f5e'}
                              strokeWidth="1"
                            />
                            <text
                              x={centerX}
                              y={Math.max(revY - 11, 21)}
                              fill={item.yoy_revenue_growth_pct >= 0 ? '#047857' : '#be123c'}
                              fontSize="10"
                              fontWeight="700"
                              textAnchor="middle"
                              fontFamily="var(--font-mono)"
                            >
                              {item.yoy_revenue_growth_pct >= 0 ? `+${item.yoy_revenue_growth_pct}%` : `${item.yoy_revenue_growth_pct}%`}
                            </text>
                          </g>
                        )}

                        {/* Revenue Bar */}
                        <rect
                          x={revX}
                          y={revY}
                          width={barW}
                          height={revH}
                          rx="4"
                          fill="url(#revGrad)"
                          className="animated-bar"
                        />

                        {/* Net Income Bar */}
                        <rect
                          x={netX}
                          y={netY}
                          width={barW}
                          height={netH}
                          rx="4"
                          fill="url(#netGrad)"
                          className="animated-bar"
                        />

                        {/* Fiscal Year Label */}
                        <text
                          x={centerX}
                          y={svgHeight - 12}
                          fill="var(--text-primary)"
                          fontSize="12"
                          fontWeight="700"
                          textAnchor="middle"
                          fontFamily="var(--font-mono)"
                        >
                          FY{item.fiscal_year}
                        </text>
                      </g>
                    );
                  })}
                </svg>

                {/* Interactive Tooltip */}
                {hoveredItem && hoveredItem.type === 'rev_net' && (
                  <div
                    className="chart-hover-popover"
                    style={{
                      left: `${(hoveredItem.x / svgWidth) * 100}%`,
                      top: `${Math.max(hoveredItem.y - 10, 10)}px`,
                    }}
                  >
                    <div className="popover-title">FY{hoveredItem.item.fiscal_year} Financial Snapshot</div>
                    <div className="popover-row">
                      <span>Revenue:</span>
                      <strong>{formatCurrency(hoveredItem.item.revenue)}</strong>
                    </div>
                    <div className="popover-row">
                      <span>Net Income:</span>
                      <strong>{formatCurrency(hoveredItem.item.net_income)}</strong>
                    </div>
                    {hoveredItem.item.net_margin !== null && (
                      <div className="popover-row">
                        <span>Net Margin:</span>
                        <strong style={{ color: '#06b6d4' }}>{hoveredItem.item.net_margin}%</strong>
                      </div>
                    )}
                    {hoveredItem.item.yoy_revenue_growth_pct !== null && (
                      <div className="popover-row">
                        <span>YoY Growth:</span>
                        <strong style={{ color: hoveredItem.item.yoy_revenue_growth_pct >= 0 ? '#10b981' : '#f43f5e' }}>
                          {hoveredItem.item.yoy_revenue_growth_pct > 0 ? `+${hoveredItem.item.yoy_revenue_growth_pct}%` : `${hoveredItem.item.yoy_revenue_growth_pct}%`}
                        </strong>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}

      {/* ── TAB 2: PROFIT MARGINS CURVE (GROSS, OPERATING, NET) ── */}
      {activeTab === 'margins' && hasSeriesData && (
        <div className="chart-body-container">
          <div className="chart-legend-row">
            <div className="legend-item">
              <span className="legend-color-dot" style={{ backgroundColor: '#f59e0b' }} />
              <span>Gross Margin (%)</span>
            </div>
            <div className="legend-item">
              <span className="legend-color-dot" style={{ backgroundColor: '#10b981' }} />
              <span>Operating Margin (%)</span>
            </div>
            <div className="legend-item">
              <span className="legend-color-dot" style={{ backgroundColor: '#06b6d4' }} />
              <span>Net Margin (%)</span>
            </div>
          </div>

          {/* SVG Margins Multi-Line Chart */}
          {(() => {
            const allMargins = series.flatMap((s) => [s.gross_margin, s.operating_margin, s.net_margin].filter((m) => m !== null));
            const maxM = Math.max(...allMargins, 50);
            const minM = Math.min(...allMargins, 0);
            const rangeM = maxM - minM || 1;

            const svgWidth = 720;
            const svgHeight = 240;
            const padding = { top: 30, right: 35, bottom: 40, left: 55 };
            const chartW = svgWidth - padding.left - padding.right;
            const chartH = svgHeight - padding.top - padding.bottom;

            const getX = (idx) => padding.left + (idx / (series.length - 1 || 1)) * chartW;
            const getY = (val) => padding.top + chartH - ((val - minM) / rangeM) * chartH;

            const makePath = (key) =>
              series
                .map((s, idx) => {
                  const val = s[key];
                  if (val === null || val === undefined) return null;
                  const x = getX(idx);
                  const y = getY(val);
                  return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
                })
                .filter(Boolean)
                .join(' ');

            const grossPath = makePath('gross_margin');
            const opPath = makePath('operating_margin');
            const netPath = makePath('net_margin');

            return (
              <div style={{ position: 'relative' }}>
                <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="financial-svg-canvas">
                  {/* Gridlines */}
                  {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
                    const y = padding.top + chartH * (1 - ratio);
                    const labelVal = minM + rangeM * ratio;
                    return (
                      <g key={idx}>
                        <line
                          x1={padding.left}
                          y1={y}
                          x2={padding.left + chartW}
                          y2={y}
                          stroke="var(--border-subtle)"
                          strokeDasharray="3 3"
                        />
                        <text
                          x={padding.left - 8}
                          y={y + 4}
                          fill="var(--text-muted)"
                          fontSize="10"
                          textAnchor="end"
                          fontFamily="var(--font-mono)"
                        >
                          {labelVal.toFixed(1)}%
                        </text>
                      </g>
                    );
                  })}

                  {/* Lines */}
                  {grossPath && (
                    <path
                      d={grossPath}
                      fill="none"
                      stroke="#f59e0b"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  )}
                  {opPath && (
                    <path
                      d={opPath}
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="3.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  )}
                  {netPath && (
                    <path
                      d={netPath}
                      fill="none"
                      stroke="#06b6d4"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  )}

                  {/* Nodes & Year Labels */}
                  {series.map((s, idx) => {
                    const x = getX(idx);
                    return (
                      <g key={s.fiscal_year}>
                        {s.operating_margin !== null && (
                          <circle
                            cx={x}
                            cy={getY(s.operating_margin)}
                            r="5.5"
                            fill="#ffffff"
                            stroke="#10b981"
                            strokeWidth="3"
                            style={{ cursor: 'pointer' }}
                            onMouseEnter={() => setHoveredItem({ type: 'margin', item: s, x, y: getY(s.operating_margin) })}
                            onMouseLeave={() => setHoveredItem(null)}
                          />
                        )}
                        <text
                          x={x}
                          y={svgHeight - 12}
                          fill="var(--text-primary)"
                          fontSize="12"
                          fontWeight="700"
                          textAnchor="middle"
                          fontFamily="var(--font-mono)"
                        >
                          FY{s.fiscal_year}
                        </text>
                      </g>
                    );
                  })}
                </svg>

                {hoveredItem && hoveredItem.type === 'margin' && (
                  <div
                    className="chart-hover-popover"
                    style={{
                      left: `${(hoveredItem.x / svgWidth) * 100}%`,
                      top: `${Math.max(hoveredItem.y - 10, 10)}px`,
                    }}
                  >
                    <div className="popover-title">FY{hoveredItem.item.fiscal_year} Margin Breakdown</div>
                    {hoveredItem.item.gross_margin !== null && (
                      <div className="popover-row">
                        <span>Gross Margin:</span>
                        <strong style={{ color: '#f59e0b' }}>{hoveredItem.item.gross_margin}%</strong>
                      </div>
                    )}
                    {hoveredItem.item.operating_margin !== null && (
                      <div className="popover-row">
                        <span>Operating Margin:</span>
                        <strong style={{ color: '#10b981' }}>{hoveredItem.item.operating_margin}%</strong>
                      </div>
                    )}
                    {hoveredItem.item.net_margin !== null && (
                      <div className="popover-row">
                        <span>Net Margin:</span>
                        <strong style={{ color: '#06b6d4' }}>{hoveredItem.item.net_margin}%</strong>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}

      {/* ── TAB 3: CASH FLOW & ACCRUAL CONVERSION ── */}
      {activeTab === 'cash_flow' && hasSeriesData && (
        <div className="chart-body-container">
          <div className="chart-legend-row">
            <div className="legend-item">
              <span className="legend-color-dot" style={{ backgroundColor: '#059669' }} />
              <span>Operating Cash Flow ($B)</span>
            </div>
            <div className="legend-item">
              <span className="legend-color-dot" style={{ backgroundColor: '#0284c7' }} />
              <span>Free Cash Flow ($B)</span>
            </div>
            <div className="legend-item">
              <span className="legend-color-dot" style={{ backgroundColor: '#94a3b8' }} />
              <span>Reported Net Income ($B)</span>
            </div>
          </div>

          {/* SVG Cash Flow Bars */}
          {(() => {
            const maxVal = Math.max(...series.map((s) => Math.max(s.operating_cash_flow || 0, s.net_income || 0)), 1);
            const svgWidth = 720;
            const svgHeight = 240;
            const padding = { top: 30, right: 30, bottom: 40, left: 65 };
            const chartW = svgWidth - padding.left - padding.right;
            const chartH = svgHeight - padding.top - padding.bottom;

            const groupW = chartW / series.length;
            const barW = Math.min(groupW * 0.26, 32);

            return (
              <div style={{ position: 'relative' }}>
                <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="financial-svg-canvas">
                  {/* Gridlines */}
                  {[0, 0.5, 1].map((ratio, idx) => {
                    const y = padding.top + chartH * (1 - ratio);
                    const labelVal = maxVal * ratio;
                    return (
                      <g key={idx}>
                        <line
                          x1={padding.left}
                          y1={y}
                          x2={padding.left + chartW}
                          y2={y}
                          stroke="var(--border-subtle)"
                          strokeDasharray="3 3"
                        />
                        <text
                          x={padding.left - 8}
                          y={y + 4}
                          fill="var(--text-muted)"
                          fontSize="10"
                          textAnchor="end"
                          fontFamily="var(--font-mono)"
                        >
                          {formatCurrency(labelVal)}
                        </text>
                      </g>
                    );
                  })}

                  {series.map((item, idx) => {
                    const groupX = padding.left + idx * groupW;
                    const centerX = groupX + groupW / 2;

                    const ocfH = item.operating_cash_flow ? Math.max((item.operating_cash_flow / maxVal) * chartH, 4) : 0;
                    const fcfH = item.free_cash_flow ? Math.max((item.free_cash_flow / maxVal) * chartH, 3) : 0;
                    const netH = item.net_income ? Math.max((item.net_income / maxVal) * chartH, 2) : 0;

                    const ocfX = centerX - barW * 1.5 - 2;
                    const fcfX = centerX - barW * 0.5;
                    const netX = centerX + barW * 0.5 + 2;

                    const ocfY = padding.top + chartH - ocfH;
                    const fcfY = padding.top + chartH - fcfH;
                    const netY = padding.top + chartH - netH;

                    return (
                      <g
                        key={item.fiscal_year}
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={() => setHoveredItem({ type: 'cf', item, x: centerX, y: ocfY })}
                        onMouseLeave={() => setHoveredItem(null)}
                      >
                        {/* Cash conversion badge */}
                        {item.cash_conversion_pct !== null && (
                          <text
                            x={centerX}
                            y={Math.max(ocfY - 10, 15)}
                            fill="#059669"
                            fontSize="10"
                            fontWeight="800"
                            textAnchor="middle"
                            fontFamily="var(--font-mono)"
                          >
                            {item.cash_conversion_pct}% Conv
                          </text>
                        )}

                        <rect x={ocfX} y={ocfY} width={barW} height={ocfH} rx="3" fill="#059669" />
                        <rect x={fcfX} y={fcfY} width={barW} height={fcfH} rx="3" fill="#0284c7" />
                        <rect x={netX} y={netY} width={barW} height={netH} rx="3" fill="#94a3b8" />

                        <text
                          x={centerX}
                          y={svgHeight - 12}
                          fill="var(--text-primary)"
                          fontSize="12"
                          fontWeight="700"
                          textAnchor="middle"
                          fontFamily="var(--font-mono)"
                        >
                          FY{item.fiscal_year}
                        </text>
                      </g>
                    );
                  })}
                </svg>

                {hoveredItem && hoveredItem.type === 'cf' && (
                  <div
                    className="chart-hover-popover"
                    style={{
                      left: `${(hoveredItem.x / svgWidth) * 100}%`,
                      top: `${Math.max(hoveredItem.y - 10, 10)}px`,
                    }}
                  >
                    <div className="popover-title">FY{hoveredItem.item.fiscal_year} Cash Conversion</div>
                    <div className="popover-row">
                      <span>Operating Cash Flow:</span>
                      <strong style={{ color: '#059669' }}>{formatCurrency(hoveredItem.item.operating_cash_flow)}</strong>
                    </div>
                    <div className="popover-row">
                      <span>Free Cash Flow:</span>
                      <strong style={{ color: '#0284c7' }}>{formatCurrency(hoveredItem.item.free_cash_flow)}</strong>
                    </div>
                    <div className="popover-row">
                      <span>Net Income:</span>
                      <strong>{formatCurrency(hoveredItem.item.net_income)}</strong>
                    </div>
                    {hoveredItem.item.cash_conversion_pct !== null && (
                      <div className="popover-row">
                        <span>Cash / Earnings:</span>
                        <strong style={{ color: '#059669' }}>{hoveredItem.item.cash_conversion_pct}%</strong>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}

      {/* ── TAB 4: PEER BENCHMARK BARS ── */}
      {activeTab === 'peer' && isComparison && (
        <div className="comparison-bar-container">
          <div className="bars-wrapper">
            {ratios.map((r, idx) => {
              const pct = typeof r.value === 'number' ? r.value * 100 : parseFloat(r.percentage_str || r.result_formatted) || 0;
              const maxVal = Math.max(...ratios.map((item) => typeof item.value === 'number' ? item.value * 100 : parseFloat(item.percentage_str || item.result_formatted) || 0), 1);
              const barWidthPct = Math.min(Math.max((pct / maxVal) * 88, 12), 98);
              const isFirst = idx === 0;

              return (
                <div key={idx} className="comparison-bar-row">
                  <div className="bar-label-col">
                    <span className="bar-company-name">{r.company || r.name || `Peer ${idx + 1}`}</span>
                    <span className="bar-pct-tag">{r.result_formatted || r.percentage_str || `${pct.toFixed(2)}%`}</span>
                  </div>
                  <div className="bar-track-col">
                    <div
                      className="bar-fill"
                      style={{
                        width: `${barWidthPct}%`,
                        backgroundColor: isFirst ? 'var(--accent-primary)' : '#06b6d4',
                      }}
                    >
                      <span className="bar-inner-text">{r.result_formatted || r.percentage_str || `${pct.toFixed(2)}%`}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {spread && (
            <div className="chart-footer-note">
              <Sparkles size={14} color="var(--accent-primary)" />
              <span>{spread.summary || `${spread.spread_bps} bps peer differential`} (Deterministically verified via XBRL tags)</span>
            </div>
          )}
        </div>
      )}
    </TiltCard>
  );
}
