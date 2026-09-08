import React from 'react';
import { TrendingUp, ShieldCheck, ArrowUpRight } from 'lucide-react';

const TICKER_ITEMS = [
  {
    ticker: 'AAPL',
    name: 'Apple Inc.',
    metric: 'Rev: $383.3B · R&D: $29.9B',
    query: 'What was Apple\'s revenue, R&D spend, and net income for fiscal year 2023?',
  },
  {
    ticker: 'MSFT',
    name: 'Microsoft Corp',
    metric: 'Rev: $211.9B · R&D: $27.2B',
    query: 'Compare R&D spend as % of revenue between Apple and Microsoft for FY2023',
  },
  {
    ticker: 'NVDA',
    name: 'NVIDIA Corp',
    metric: 'Rev: $60.9B · Net Inc: $29.8B',
    query: 'What was NVIDIA\'s total revenue and net income reported in their latest 10-K?',
  },
  {
    ticker: 'TSLA',
    name: 'Tesla, Inc.',
    metric: 'Auto Credits: $1.79B (FY23)',
    query: 'How has Tesla\'s automotive regulatory credits revenue trended over the last 3 fiscal years?',
  },
  {
    ticker: 'AMZN',
    name: 'Amazon.com',
    metric: 'Rev: $574.8B · AWS Segment',
    query: 'What was Amazon\'s total revenue and operating income reported in their latest 10-K?',
  },
  {
    ticker: 'GOOGL',
    name: 'Alphabet Inc.',
    metric: 'Rev: $307.4B · Net Inc: $73.8B',
    query: 'What was Alphabet\'s total revenues and research and development expense for fiscal year 2023?',
  },
  {
    ticker: 'META',
    name: 'Meta Platforms',
    metric: 'Rev: $134.9B · R&D: $38.5B',
    query: 'What was Meta\'s revenue, R&D spend, and net income for fiscal year 2023?',
  },
];

export default function TickerTape({ onSelectQuery, disabled }) {
  // Duplicate array to achieve seamless infinite marquee loop
  const doubledItems = [...TICKER_ITEMS, ...TICKER_ITEMS];

  return (
    <div className="ticker-tape-container">
      <div className="ticker-live-badge">
        <span className="ticker-pulse-dot" />
        <span>EDGAR LIVE</span>
      </div>

      <div className="ticker-tape-track">
        <div className="ticker-tape-marquee">
          {doubledItems.map((item, idx) => (
            <div
              key={idx}
              className="ticker-tape-item"
              onClick={() => !disabled && onSelectQuery(item.query)}
              title={`Click to analyze ${item.name}`}
            >
              <span className="ticker-symbol">{item.ticker}</span>
              <span className="ticker-metric">{item.metric}</span>
              <span className="ticker-status-pill">10-K Filed</span>
              <ArrowUpRight size={12} className="ticker-arrow" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
