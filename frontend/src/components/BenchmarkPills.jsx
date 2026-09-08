import React from 'react';
import { Sparkles, TrendingUp, ShieldAlert, Scale, Cpu, SearchX } from 'lucide-react';

const SAMPLE_QUESTIONS = [
  {
    icon: <TrendingUp size={14} color="#0284c7" />,
    label: "AAPL vs MSFT R&D %",
    query: "Compare R&D spend as % of revenue between Apple and Microsoft over the last 2 years.",
  },
  {
    icon: <ShieldAlert size={14} color="#7c3aed" />,
    label: "MSFT Cybersecurity (Item 1C)",
    query: "What cybersecurity risk management and governance did Microsoft disclose?",
  },
  {
    icon: <Scale size={14} color="#db2777" />,
    label: "Apple DMA Litigation (Item 3)",
    query: "What legal proceedings regarding the Digital Markets Act did Apple disclose?",
  },
  {
    icon: <Cpu size={14} color="#059669" />,
    label: "Tesla FSD & AI (Item 1)",
    query: "What Full Self-Driving and AI products did Tesla highlight in Item 1?",
  },
  {
    icon: <SearchX size={14} color="#e11d48" />,
    label: "Negative Test: Vision Pro R&D",
    query: "What was Apple's R&D spend broken down specifically for the Apple Vision Pro product line?",
  },
  {
    icon: <TrendingUp size={14} color="#d97706" />,
    label: "Apple Net Income (FY2025)",
    query: "What was Apple's Net Income for fiscal year 2025?",
  },
];

export default function BenchmarkPills({ onSelectQuery, disabled }) {
  return (
    <div className="benchmarks-wrap">
      <div className="benchmarks-label">
        <Sparkles size={13} color="#0f766e" />
        <span>Verified Benchmark Queries (1-Click Run)</span>
      </div>
      <div className="chips-grid">
        {SAMPLE_QUESTIONS.map((q, idx) => (
          <button
            key={idx}
            type="button"
            className="benchmark-chip"
            onClick={() => onSelectQuery(q.query)}
            disabled={disabled}
          >
            {q.icon}
            <span>{q.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
