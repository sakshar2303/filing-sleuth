import React, { useState, useEffect, useRef } from 'react';
import { Search, ArrowRight, X, Building2, Sparkles, Database } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

export default function QueryInput({ onSubmit, isLoading, currentQuery, setQuery }) {
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [isSearchingCompanies, setIsSearchingCompanies] = useState(false);
  const wrapperRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch suggestions with debounce when currentQuery changes
  useEffect(() => {
    // If user is typing a word that looks like a ticker or company name search
    const trimmed = currentQuery.trim();
    if (!trimmed) {
      setSuggestions([]);
      return;
    }

    // Extract the last word or whole query if short
    const words = trimmed.split(' ');
    const lastWord = words[words.length - 1];

    if (lastWord.length >= 2 && lastWord.length <= 6) {
      const timer = setTimeout(async () => {
        try {
          setIsSearchingCompanies(true);
          const res = await fetch(`${API_BASE}/api/companies?q=${encodeURIComponent(lastWord)}&limit=6`);
          if (res.ok) {
            const data = await res.json();
            if (data.companies && data.companies.length > 0) {
              setSuggestions(data.companies);
              setShowDropdown(true);
            } else {
              setSuggestions([]);
            }
          }
        } catch (e) {
          // Silent fallback
        } finally {
          setIsSearchingCompanies(false);
        }
      }, 250);

      return () => clearTimeout(timer);
    } else {
      setShowDropdown(false);
    }
  }, [currentQuery]);

  const handleSelectCompany = (comp) => {
    // If the input already has some text, replace the last word or append
    const words = currentQuery.trim().split(' ');
    const lastWord = words[words.length - 1];

    if (words.length <= 1) {
      // Start a standard template
      setQuery(`What was ${comp.name}'s (${comp.ticker}) revenue, R&D spend, and net income for FY2023?`);
    } else {
      words[words.length - 1] = comp.ticker;
      setQuery(words.join(' ') + ' ');
    }
    setShowDropdown(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      setShowDropdown(false);
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      setShowDropdown(false);
      if (currentQuery.trim() && !isLoading) {
        onSubmit(currentQuery.trim());
      }
    }
  };

  return (
    <div className="search-container" ref={wrapperRef} style={{ position: 'relative' }}>
      <div className="search-bar-wrap">
        <Search size={20} color="#0f766e" style={{ marginRight: '0.6rem', flexShrink: 0 }} />
        <input
          type="text"
          className="search-input"
          placeholder="Ask anything across Apple, Microsoft, Tesla 10-K filings (e.g. Compare R&D % of revenue)..."
          value={currentQuery}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
          disabled={isLoading}
        />
        {currentQuery && (
          <button
            type="button"
            onClick={() => {
              setQuery('');
              setShowDropdown(false);
            }}
            style={{
              background: 'none',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: '0.4rem',
              marginRight: '0.5rem',
            }}
            title="Clear query"
          >
            <X size={16} />
          </button>
        )}
        <button
          type="button"
          className="search-btn"
          onClick={() => {
            setShowDropdown(false);
            if (currentQuery.trim()) onSubmit(currentQuery.trim());
          }}
          disabled={isLoading || !currentQuery.trim()}
        >
          {isLoading ? (
            <>
              <div className="spinner" />
              <span>Analyzing</span>
            </>
          ) : (
            <>
              <span>Execute</span>
              <ArrowRight size={16} />
            </>
          )}
        </button>
      </div>

      {/* Autocomplete Dropdown Popover */}
      {showDropdown && suggestions.length > 0 && (
        <div className="autocomplete-popover">
          <div className="autocomplete-header">
            <Database size={13} color="var(--accent-primary)" />
            <span>SEC Registrant Directory Match</span>
            <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: 'var(--text-muted)' }}>Press Esc to close</span>
          </div>
          <div className="autocomplete-list">
            {suggestions.map((c, i) => (
              <div
                key={i}
                className="autocomplete-item"
                onClick={() => handleSelectCompany(c)}
              >
                <div className="comp-ticker-badge">{c.ticker}</div>
                <div className="comp-name-group">
                  <div className="comp-name">{c.name}</div>
                  <div className="comp-cik">CIK: {c.cik}</div>
                </div>
                <button type="button" className="comp-insert-btn">
                  Insert
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
