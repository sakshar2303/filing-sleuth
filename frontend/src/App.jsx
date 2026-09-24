import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import WelcomePage from './components/WelcomePage';
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

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const WS_PROTOCOL = API_BASE.startsWith('https') ? 'wss' : 'ws';
const WS_BASE = `${WS_PROTOCOL}://${API_BASE.replace(/^https?:\/\//, '')}/ws/query`;

export default function App() {
  const [activeView, setActiveView] = useState('welcome'); // 'welcome' | 'workspace' | 'about'
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);

  const [skepticMode, setSkepticMode] = useState(false);
  const [currentQuery, setCurrentQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLiveStreaming, setIsLiveStreaming] = useState(false);
  const [trace, setTrace] = useState([]);
  const [result, setResult] = useState(null);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [error, setError] = useState(null);
  const [serverHealthy, setServerHealthy] = useState(false);

  // History state with persistent local storage
  const [history, setHistory] = useState(() => {
    try {
      const saved = localStorage.getItem('filing_sleuth_history');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  });

  // Dynamic ambient background glow coordinates
  const [mousePos, setMousePos] = useState({ x: 50, y: 25 });
  const handleMouseMove = (e) => {
    const x = (e.clientX / window.innerWidth) * 100;
    const y = (e.clientY / window.innerHeight) * 100;
    setMousePos({ x, y });
  };

  // Keyboard shortcut: Cmd+B / Ctrl+B to toggle sidebar
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        setIsSidebarCollapsed((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

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
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const saveToHistory = (q, resData, traceData) => {
    if (!q || !resData) return;
    const newItem = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
      question: q,
      result: resData,
      trace: traceData || [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setHistory((prev) => {
      const updated = [newItem, ...prev.filter((item) => item.question !== q)].slice(0, 15);
      try {
        localStorage.setItem('filing_sleuth_history', JSON.stringify(updated));
      } catch (e) {}
      return updated;
    });
  };

  const handleRunQuery = async (queryText, forceSkeptic = null) => {
    if (!queryText.trim() || isLoading) return;

    const isSkeptic = forceSkeptic !== null ? forceSkeptic : skepticMode;

    setActiveView('workspace');
    setCurrentQuery(queryText);
    setIsLoading(true);
    setError(null);
    setTrace([]);
    setResult(null);

    // Try WebSocket streaming first for real-time trace experience
    try {
      const ws = new WebSocket(WS_BASE);
      let receivedResult = false;
      const accumulatedTrace = [];

      ws.onopen = () => {
        setIsLiveStreaming(true);
        ws.send(JSON.stringify({ question: queryText, skeptic_mode: isSkeptic }));
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'trace') {
            accumulatedTrace.push(msg);
            setTrace((prev) => [...prev, msg]);
          } else if (msg.type === 'result') {
            receivedResult = true;
            setResult(msg.data);
            saveToHistory(queryText, msg.data, accumulatedTrace);
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
          await executeViaRest(queryText, isSkeptic);
        }
      };

      ws.onclose = () => {
        setIsLiveStreaming(false);
      };

    } catch (wsErr) {
      console.warn('WebSocket connection error, using REST fallback:', wsErr);
      await executeViaRest(queryText, isSkeptic);
    }
  };

  const executeViaRest = async (queryText, isSkeptic = false) => {
    try {
      const response = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: queryText, skeptic_mode: isSkeptic }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${response.statusText}`);
      }

      const data = await response.json();
      setTrace(data.trace || []);
      setResult(data);
      saveToHistory(queryText, data, data.trace || []);
    } catch (err) {
      setError(err.message || 'Failed to communicate with research backend.');
    } finally {
      setIsLoading(false);
      setIsLiveStreaming(false);
    }
  };

  return (
    <div
      className="app-shell"
      onMouseMove={handleMouseMove}
      style={{
        '--mouse-x': `${mousePos.x}%`,
        '--mouse-y': `${mousePos.y}%`,
      }}
    >
      {/* Collapsible Analyst Sidebar */}
      <Sidebar
        activeView={activeView}
        setActiveView={setActiveView}
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
        history={history}
        onSelectHistory={(item) => {
          setCurrentQuery(item.question);
          setResult(item.result);
          setTrace(item.trace || []);
          setActiveView('workspace');
        }}
        onClearHistory={() => {
          setHistory([]);
          localStorage.removeItem('filing_sleuth_history');
        }}
        onNewQuery={() => {
          setCurrentQuery('');
          setResult(null);
          setTrace([]);
          setActiveView('workspace');
        }}
        onSelectTicker={(ticker, name) => {
          const q = `What was ${name}'s (${ticker}) revenue, R&D spend, and net income for FY2023?`;
          setCurrentQuery(q);
          handleRunQuery(q);
        }}
      />

      {/* Main App Content Area */}
      <div className={`app-main-content ${isSidebarCollapsed ? 'sidebar-is-collapsed' : 'sidebar-is-expanded'}`}>
        <Navbar
          isStreamingActive={isLiveStreaming}
          serverHealthy={serverHealthy}
          activeView={activeView}
          setActiveView={setActiveView}
          isSidebarCollapsed={isSidebarCollapsed}
          setIsSidebarCollapsed={setIsSidebarCollapsed}
        />


        {/* Live Financial Ticker Ribbon */}
        <TickerTape
          onSelectQuery={(q) => {
            handleRunQuery(q);
          }}
          disabled={isLoading}
        />

        <main className="main-container">
          {/* VIEW 1: WELCOME & PRODUCT TOUR */}
          {activeView === 'welcome' && (
            <WelcomePage
              onOpenTerminal={() => setActiveView('workspace')}
              onLaunchQuery={(q) => {
                handleRunQuery(q);
              }}
              onOpenAbout={() => setActiveView('about')}
            />
          )}

          {/* VIEW 2: ABOUT ARCHITECTURE & 3D STACK */}
          {activeView === 'about' && (
            <AboutSection
              onSelectBenchmark={(q) => {
                handleRunQuery(q);
              }}
              onClose={() => setActiveView('workspace')}
            />
          )}

          {/* VIEW 3: RESEARCH WORKSPACE & TERMINAL */}
          {activeView === 'workspace' && (
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
                  skepticMode={skepticMode}
                  setSkepticMode={setSkepticMode}
                />

                <BenchmarkPills
                  onSelectQuery={(q) => {
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
    </div>
  );
}
