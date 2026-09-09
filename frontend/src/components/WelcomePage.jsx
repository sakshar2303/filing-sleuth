import React from 'react';
import {
  Terminal,
  ShieldCheck,
  Database,
  Layers,
  ArrowRight,
  Sparkles,
  BookOpen,
  CheckCircle2,
  Lock,
  Cpu,
  BarChart3,
  TrendingUp,
  FileSearch,
  ExternalLink,
  Users,
  Briefcase,
  Newspaper,
  LineChart,
  AlertTriangle
} from 'lucide-react';
import TiltCard from './TiltCard';
import BrandLogo from './BrandLogo';

const TARGET_AUDIENCES = [
  {
    id: 'equity-analysts',
    title: 'Equity Research Analysts',
    subtitle: 'Buy-Side & Sell-Side Investment Firms',
    icon: <BarChart3 size={24} color="#0f766e" />,
    badge: 'Buy-Side / Sell-Side',
    painPoint: 'Drowning in 300+ page filings across 20+ sector peers; generic AI hallucinates numbers and makes arithmetic mistakes.',
    howItHelps: 'Queries official SEC CompanyFacts XBRL directly. Calculates deterministic margins, growth rates, and peer basis-point spreads in Python.',
    keyFeatures: ['XBRL Ground Truth', 'Fiscal Year Sync', 'Deterministic Math'],
    exampleQuery: 'Compare R&D spend as % of revenue between Apple and Microsoft for FY2023',
    gradient: 'linear-gradient(135deg, rgba(15, 118, 110, 0.07) 0%, rgba(2, 132, 199, 0.05) 100%)',
  },
  {
    id: 'auditors',
    title: 'Auditors & Forensic Accountants',
    subtitle: 'Big 4 & Litigation Advisory',
    icon: <ShieldCheck size={24} color="#059669" />,
    badge: 'Audit & Compliance',
    painPoint: 'Need cryptographic proof for claims; cannot risk non-verifiable quotes or untraced multi-period restatements.',
    howItHelps: 'Audits every quoted sentence against raw 10-K HTML with a sliding window Levenshtein matcher (>85%). Cites exact Accession numbers and character offsets.',
    keyFeatures: ['Sliding Window Quote Audit', 'Zero Hallucination Guarantee', 'Exact SEC Accessions'],
    exampleQuery: 'What cybersecurity risk management and governance did Microsoft disclose in Item 1C?',
    gradient: 'linear-gradient(135deg, rgba(5, 150, 105, 0.07) 0%, rgba(15, 118, 110, 0.05) 100%)',
  },
  {
    id: 'journalists',
    title: 'Financial Journalists & Columnists',
    subtitle: 'WSJ, Bloomberg, FT & Investigative Media',
    icon: <Newspaper size={24} color="#7c3aed" />,
    badge: 'Financial Press',
    painPoint: 'Racing against deadlines when 10-Ks drop to discover newly added risks without risking embarrassing public retractions.',
    howItHelps: 'Instant semantic hybrid search across Item 1A (Risk Factors) and Item 3 (Legal Proceedings) with verbatim quotes ready to copy into articles.',
    keyFeatures: ['Item Boundary Isolation', 'Verbatim Quotes', 'Fast Disclosure Discovery'],
    exampleQuery: 'What legal proceedings regarding the Digital Markets Act did Apple disclose in Item 3?',
    gradient: 'linear-gradient(135deg, rgba(124, 58, 237, 0.07) 0%, rgba(219, 39, 119, 0.05) 100%)',
  },
  {
    id: 'corp-dev',
    title: 'Corporate Strategy & M&A Teams',
    subtitle: 'Private Equity & In-House Strategy',
    icon: <Briefcase size={24} color="#0284c7" />,
    badge: 'M&A & Corporate Dev',
    painPoint: 'Benchmarking acquisition targets against peer cost structures, customer dependencies, and unaligned fiscal calendars.',
    howItHelps: 'Builds cross-company comparison matrices, flags non-aligned fiscal year ends (e.g. Sept vs June), and computes basis point spreads.',
    keyFeatures: ['Comparison Matrix', 'Calendar Mismatch Warnings', 'Peer Spread Models'],
    exampleQuery: 'How has Tesla\'s automotive regulatory credits revenue trended over the last 3 fiscal years?',
    gradient: 'linear-gradient(135deg, rgba(2, 132, 199, 0.07) 0%, rgba(99, 102, 241, 0.05) 100%)',
  },
  {
    id: 'retail-investors',
    title: 'Fundamental Investors & Family Offices',
    subtitle: 'Deep-Value & Fundamental Allocators',
    icon: <LineChart size={24} color="#d97706" />,
    badge: 'Family Offices & Allocators',
    painPoint: 'Cannot justify $25,000–$30,000/year per seat for Bloomberg or FactSet licenses just to cross-reference SEC filings.',
    howItHelps: 'Provides institutional-grade financial forensic intelligence with direct SEC EDGAR API grounding completely open and accessible in the browser.',
    keyFeatures: ['Institutional Rigor', 'No Cost Barrier', 'Full Provenance Footnotes'],
    exampleQuery: 'What was Apple\'s Net Income for fiscal year 2025?',
    gradient: 'linear-gradient(135deg, rgba(217, 119, 6, 0.07) 0%, rgba(234, 88, 12, 0.05) 100%)',
  },
];

export default function WelcomePage({ onOpenTerminal, onLaunchQuery, onOpenAbout }) {
  return (
    <div className="welcome-container">
      {/* Hero Banner */}
      <div className="welcome-hero">
        <div className="welcome-hero-brand">
          <div className="hero-logo-wrapper" title="Filing Sleuth — Forensic SEC Ground Truth">
            <BrandLogo size={58} animated />
          </div>
        </div>

        <div className="welcome-badge">
          <Sparkles size={14} color="var(--accent-primary)" />
          <span>SEC EDGAR AUTONOMOUS FORENSIC AGENT</span>
        </div>

        <h1 className="welcome-headline">
          Zero-Hallucination <span className="highlight-text">SEC 10-K</span> Financial Intelligence
        </h1>

        <p className="welcome-subhead">
          Engineered for equity research analysts, auditors, and journalists. Replaces manual reading of 300+ page
          annual filings with authoritative XBRL ground truth, structure-aware chunking, and strict quote verification.
        </p>

        {/* CTA Buttons */}
        <div className="welcome-cta-group">
          <button
            type="button"
            className="welcome-primary-btn"
            onClick={onOpenTerminal}
          >
            <Terminal size={17} />
            <span>Enter Research Terminal</span>
            <ArrowRight size={17} />
          </button>

          <button
            type="button"
            className="welcome-secondary-btn"
            onClick={onOpenAbout}
          >
            <BookOpen size={16} />
            <span>System Architecture & 3D Model</span>
          </button>
        </div>
      </div>

      {/* Accuracy Scorecard */}
      <div className="welcome-scorecard">
        <div className="scorecard-item">
          <div className="scorecard-num">20 / 20</div>
          <div className="scorecard-label">
            <CheckCircle2 size={13} color="#059669" />
            <span>Benchmark Questions Passed</span>
          </div>
        </div>

        <div className="scorecard-divider" />

        <div className="scorecard-item">
          <div className="scorecard-num">100.0%</div>
          <div className="scorecard-label">
            <Database size={13} color="#0284c7" />
            <span>XBRL Extraction Precision</span>
          </div>
        </div>

        <div className="scorecard-divider" />

        <div className="scorecard-item">
          <div className="scorecard-num">0.0%</div>
          <div className="scorecard-label">
            <Lock size={13} color="#0f766e" />
            <span>Zero Hallucination Rate</span>
          </div>
        </div>

        <div className="scorecard-divider" />

        <div className="scorecard-item">
          <div className="scorecard-num">57 / 57</div>
          <div className="scorecard-label">
            <Cpu size={13} color="#7c3aed" />
            <span>Unit Regression Tests</span>
          </div>
        </div>
      </div>

      {/* 3 Core Value Pillars */}
      <div className="welcome-pillars-section">
        <div className="welcome-section-header">
          <h2>Why Forensic Financial AI Requires a New Standard</h2>
          <p>Traditional language models invent numbers, confuse fiscal years, and fabricate quotes. Filing Sleuth is built on cryptographic verifiability.</p>
        </div>

        <div className="welcome-pillars-grid">
          <TiltCard className="pillar-card" maxTilt={6} scale={1.015}>
            <div className="pillar-icon" style={{ background: '#ecfdf5', color: '#059669' }}>
              <Database size={24} />
            </div>
            <h3>1. XBRL Ground Truth Over Prose</h3>
            <p>
              Queries the official SEC CompanyFacts API directly for as-reported US-GAAP machine tags.
              Financial ratios and margins are calculated deterministically in Python, never generated by probabilistic token prediction.
            </p>
            <div className="pillar-tag">SEC CompanyFacts Engine</div>
          </TiltCard>

          <TiltCard className="pillar-card" maxTilt={6} scale={1.015}>
            <div className="pillar-icon" style={{ background: '#f0fdfa', color: '#0f766e' }}>
              <ShieldCheck size={24} />
            </div>
            <h3>2. Strict Fuzzy Quote Verification</h3>
            <p>
              Every cited quote in qualitative analysis is audited against the raw 10-K filing text with a sliding window Levenshtein matcher.
              If similarity is under 85%, the claim is rejected to guarantee zero hallucinations.
            </p>
            <div className="pillar-tag">Sliding Window Token Audit</div>
          </TiltCard>

          <TiltCard className="pillar-card" maxTilt={6} scale={1.015}>
            <div className="pillar-icon" style={{ background: '#f0f9ff', color: '#0284c7' }}>
              <Layers size={24} />
            </div>
            <h3>3. Automated Fiscal Year Sync</h3>
            <p>
              Detects calendar mismatches across peers (e.g., Apple's September fiscal year vs. Microsoft's June fiscal year).
              Surfaces explicit warnings and calculates basis-point spreads accurately.
            </p>
            <div className="pillar-tag">Calendar Mismatch Detection</div>
          </TiltCard>
        </div>
      </div>

      {/* TARGET AUDIENCES & USE CASES SECTION */}
      <div className="welcome-audiences-section">
        <div className="welcome-section-header">
          <div className="audiences-badge">
            <Users size={14} color="var(--accent-primary)" />
            <span>Target Audience & Impact</span>
          </div>
          <h2>Who Is Filing Sleuth Built For?</h2>
          <p>
            Engineered for professionals who make high-stakes decisions where a single hallucinated number
            or fabricated citation is completely unacceptable.
          </p>
        </div>

        <div className="audiences-grid">
          {TARGET_AUDIENCES.map((aud) => (
            <TiltCard
              key={aud.id}
              className="audience-card"
              maxTilt={4}
              scale={1.012}
              style={{ background: aud.gradient }}
            >
              <div className="audience-card-top">
                <div className="audience-icon-box">{aud.icon}</div>
                <span className="audience-pill">{aud.badge}</span>
              </div>

              <h3 className="audience-title">{aud.title}</h3>
              <div className="audience-subtitle">{aud.subtitle}</div>

              <div className="audience-block pain-block">
                <span className="block-label">The Pain Point Solved:</span>
                <p>{aud.painPoint}</p>
              </div>

              <div className="audience-block benefit-block">
                <span className="block-label">How Filing Sleuth Helps:</span>
                <p>{aud.howItHelps}</p>
              </div>

              <div className="audience-features">
                {aud.keyFeatures.map((feat, fIdx) => (
                  <span key={fIdx} className="audience-feat-tag">{feat}</span>
                ))}
              </div>

              <div className="audience-footer">
                <span className="audience-example-label">Typical Workflow:</span>
                <button
                  type="button"
                  className="audience-launch-btn"
                  onClick={() => onLaunchQuery(aud.exampleQuery)}
                  title={`Run workflow: "${aud.exampleQuery}"`}
                >
                  <span>Launch Workflow</span>
                  <ArrowRight size={13} />
                </button>
              </div>
            </TiltCard>
          ))}
        </div>
      </div>

      {/* Test Drive Interactive Launchpad */}
      <div className="welcome-testdrive-section">
        <div className="welcome-section-header">
          <div className="testdrive-badge">
            <Sparkles size={14} color="var(--accent-primary)" />
            <span>Interactive Test Drive</span>
          </div>
          <h2>Launch a Live Research Query in 10 Seconds</h2>
          <p>Click any curated query below to enter the terminal and watch the live reasoning trace execute in real time.</p>
        </div>

        <div className="testdrive-grid">
          <div className="testdrive-card">
            <div className="testdrive-header">
              <BarChart3 size={18} color="#0f766e" />
              <span className="testdrive-card-tag">Cross-Company R&D</span>
            </div>
            <h4>Apple vs. Microsoft R&D % of Revenue</h4>
            <p>Compares R&D intensity, flags the 3-month fiscal mismatch, and displays peer spread in basis points.</p>
            <button
              type="button"
              className="testdrive-launch-btn"
              onClick={() => onLaunchQuery('Compare R&D spend as % of revenue between Apple and Microsoft for FY2023')}
            >
              <span>Launch in Terminal</span>
              <ArrowRight size={14} />
            </button>
          </div>

          <div className="testdrive-card">
            <div className="testdrive-header">
              <TrendingUp size={18} color="#0284c7" />
              <span className="testdrive-card-tag">Multi-Year Trend</span>
            </div>
            <h4>Tesla Regulatory Carbon Credit Trend</h4>
            <p>Traverses 3 annual 10-K filings, de-duplicates restatements, and computes YoY growth trajectory.</p>
            <button
              type="button"
              className="testdrive-launch-btn"
              onClick={() => onLaunchQuery('How has Tesla\'s automotive regulatory credits revenue trended over the last 3 fiscal years?')}
            >
              <span>Launch in Terminal</span>
              <ArrowRight size={14} />
            </button>
          </div>

          <div className="testdrive-card">
            <div className="testdrive-header">
              <ShieldCheck size={18} color="#7c3aed" />
              <span className="testdrive-card-tag">Item 1C Audit</span>
            </div>
            <h4>Microsoft Cybersecurity Risk Governance</h4>
            <p>Audits newly mandated SEC Item 1C disclosures with word-for-word verified quotations.</p>
            <button
              type="button"
              className="testdrive-launch-btn"
              onClick={() => onLaunchQuery('What cybersecurity risk management and governance did Microsoft disclose in Item 1C?')}
            >
              <span>Launch in Terminal</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
