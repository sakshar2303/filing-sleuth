import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import TickerTape from './components/TickerTape';
import QueryInput from './components/QueryInput';
import BenchmarkPills from './components/BenchmarkPills';
import ReasoningTrace from './components/ReasoningTrace';
import ResultReport from './components/ResultReport';
import CitationModal from './components/CitationModal';
import AboutSection from './components/AboutSection';
import AnalystLaunchpad from './components/AnalystLaunchpad';
import Footer from './components/Footer';
import { AlertCircle, FileSearch, Sparkles, BookOpen, ArrowRight } from 'lucide-react';

const API_BASE = 'http://localhost:8000';
const WS_BASE = 'ws://localhost:8000/ws/query';

export default function App() {
  const [activeView, setActiveView] = useState('workspace'); // 'workspace' | 'about'
  const [currentQuery, setCurrentQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLiveStreaming, setIsLiveStreaming] = useState(false);
  const [trace, setTrace] = useState([]);
  const [result, setResult] = useState(null);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [error, setError] = useState(null);
  const [serverHealthy, setServerHealthy] = useState(false);

  // Dynamic ambient background glow coordinates
  const [mousePos, setMousePos] = useState({ x: 50, y: 25 });
  const handleMouseMove = (e) => {
    const x = (e.clientX / window.innerWidth) * 100;
    const y = (e.clientY / window.innerHeight) * 100;
    setMousePos({ x, y });
  };



  // Check backend server health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (res.ok) setServerHealthy(true);
      } catch (err) {
        setServerHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 8000);
    return () => clearInterval(interval);
  }, []);

  const handleRunQuery = async (queryText) => {
    if (!queryText.trim() || isLoading) return;

    setCurrentQuery(queryText);
    setIsLoading(true);
    setError(null);
    setTrace([]);
    setResult(null);

    // Try WebSocket streaming first for real-time trace experience
    try {
      const ws = new WebSocket(WS_BASE);
      let receivedResult = false;

      ws.onopen = () => {
        setIsLiveStreaming(true);
        ws.send(JSON.stringify({ question: queryText }));
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'trace') {
            setTrace((prev) => [...prev, msg]);
          } else if (msg.type === 'result') {
            receivedResult = true;
            setResult(msg.data);
            setIsLoading(false);
            setIsLiveStreaming(false);
            ws.close();
          } else if (msg.type === 'error') {
            setError(msg.message || 'Pipeline execution failed.');
            setIsLoading(false);
            setIsLiveStreaming(false);
            ws.close();
          }
        } catch (e) {
          console.error('WS parse error:', e);
        }
      };

      ws.onerror = async () => {
        console.warn('WebSocket failed, falling back to REST endpoint...');
        if (!receivedResult) {
          await executeViaRest(queryText);
        }
      };

      ws.onclose = () => {
        setIsLiveStreaming(false);
      };

    } catch (wsErr) {
      console.warn('WebSocket connection error, using REST fallback:', wsErr);
      await executeViaRest(queryText);
    }
  };

  const executeViaRest = async (queryText) => {
    try {
      const response = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: queryText }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${response.statusText}`);
      }

      const data = await response.json();
      setTrace(data.trace || []);
      setResult(data);
    } catch (err) {
      setError(err.message || 'Failed to communicate with research backend.');
    } finally {
      setIsLoading(false);
      setIsLiveStreaming(false);
    }
  };

  return (
    <div
      className="app-layout"
      onMouseMove={handleMouseMove}
      style={{
        '--mouse-x': `${mousePos.x}%`,
        '--mouse-y': `${mousePos.y}%`,
      }}
    >
      <Navbar
        isStreamingActive={isLiveStreaming}
        serverHealthy={serverHealthy}
        activeView={activeView}
        setActiveView={setActiveView}
      />

      {/* Live Financial Ticker Ribbon */}
      <TickerTape
        onSelectQuery={(q) => {
          setActiveView('workspace');
          setCurrentQuery(q);
          handleRunQuery(q);
        }}
        disabled={isLoading}
      />

      <main className="main-container">
        {activeView === 'about' ? (
          <AboutSection
            onSelectBenchmark={(q) => {
              setActiveView('workspace');
              setCurrentQuery(q);
              handleRunQuery(q);
            }}
            onClose={() => setActiveView('workspace')}
          />
        ) : (
          <>
            <section className="hero-section">
              <h1 className="hero-headline">Forensic SEC EDGAR Intelligence</h1>
              <p className="hero-subhead">
                Cross-reference 10-K disclosures, verify XBRL numeric ground truth, calculate deterministic ratios,
                and inspect verbatim quotations with guaranteed zero-hallucination provenance.
              </p>

              {/* Quick Guide Trigger Pill */}
              <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1.5rem' }}>
                <button
                  type="button"
                  onClick={() => setActiveView('about')}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.45rem',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    color: 'var(--accent-primary)',
                    background: 'var(--accent-light)',
                    border: '1px solid var(--teal-border)',
                    padding: '0.35rem 0.9rem',
                    borderRadius: '20px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.background = '#e6fffa';
                    e.currentTarget.style.borderColor = 'var(--accent-primary)';
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.background = 'var(--accent-light)';
                    e.currentTarget.style.borderColor = 'var(--teal-border)';
                  }}
                >
                  <BookOpen size={14} />
                  <span>How Filing Sleuth works & how to use it effectively</span>
                  <ArrowRight size={13} />
                </button>
              </div>

              <QueryInput
                currentQuery={currentQuery}
                setQuery={setCurrentQuery}
                onSubmit={handleRunQuery}
                isLoading={isLoading}
              />

              <BenchmarkPills
                onSelectQuery={(q) => {
                  setCurrentQuery(q);
                  handleRunQuery(q);
                }}
                disabled={isLoading}
              />
            </section>

            {/* Error state */}
            {error && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  background: 'var(--rose-bg)',
                  border: '1px solid var(--rose-border)',
                  borderRadius: '10px',
                  padding: '1rem 1.5rem',
                  color: 'var(--rose-text)',
                  marginBottom: '2rem',
                }}
              >
                <AlertCircle size={20} color="#e11d48" />
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>Research Pipeline Error</div>
                  <div style={{ fontSize: '0.85rem' }}>{error}</div>
                </div>
              </div>
            )}

            {/* Agent Reasoning Trace */}
            <ReasoningTrace trace={trace} isLive={isLiveStreaming} />

            {/* Synthesis Results & Citations OR Rich Analyst Launchpad */}
            {result ? (
              <ResultReport
                result={result}
                onSelectCitation={(cit) => setSelectedCitation(cit)}
              />
            ) : !isLoading && !error && (
              <AnalystLaunchpad
                onSelectQuery={(q) => {
                  setCurrentQuery(q);
                  handleRunQuery(q);
                }}
                disabled={isLoading}
              />
            )}
          </>
        )}
      </main>

      {/* Institutional Footer */}
      <Footer onSwitchView={(view) => setActiveView(view)} />

      {/* Citation Modal Drawer */}
      <CitationModal
        citation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
      />
    </div>
  );
}

