import React, { useState } from 'react';
import { Search, ArrowRight, X } from 'lucide-react';

export default function QueryInput({ onSubmit, isLoading, currentQuery, setQuery }) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (currentQuery.trim() && !isLoading) {
        onSubmit(currentQuery.trim());
      }
    }
  };

  return (
    <div className="search-container">
      <div className="search-bar-wrap">
        <Search size={20} color="#0f766e" style={{ marginRight: '0.6rem', flexShrink: 0 }} />
        <input
          type="text"
          className="search-input"
          placeholder="Ask anything across Apple, Microsoft, Tesla 10-K filings (e.g. Compare R&D % of revenue)..."
          value={currentQuery}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        {currentQuery && (
          <button
            type="button"
            onClick={() => setQuery('')}
            style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: '0.4rem', marginRight: '0.5rem' }}
            title="Clear query"
          >
            <X size={16} />
          </button>
        )}
        <button
          type="button"
          className="search-btn"
          onClick={() => currentQuery.trim() && onSubmit(currentQuery.trim())}
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
    </div>
  );
}
