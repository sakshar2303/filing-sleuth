import React from 'react';
import { X, ExternalLink, ShieldCheck, Database, FileText } from 'lucide-react';

export default function CitationModal({ citation, onClose }) {
  if (!citation) return null;

  const rawAccn = (citation.accession_number || '').replace(/-/g, '');
  const edgarUrl = citation.accession_number && citation.cik
    ? `https://www.sec.gov/Archives/edgar/data/${citation.cik.replace(/^0+/, '')}/${rawAccn}/${citation.accession_number}-index.htm`
    : null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span className="citation-num" style={{ fontSize: '1.1rem' }}>{citation.citation_id}</span>
            <h3 style={{ fontSize: '1.2rem', color: '#0f172a' }}>{citation.company}</h3>
            {citation.source_type === 'XBRL' ? (
              <span className="badge badge-xbrl"><Database size={12} /> XBRL Ground Truth</span>
            ) : citation.quote_verified ? (
              <span className="badge badge-verified"><ShieldCheck size={12} /> Verified Quote</span>
            ) : (
              <span className="badge badge-verified"><FileText size={12} /> Text Disclosure</span>
            )}
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Exact Quote */}
          {citation.exact_quote && (
            <div>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#475569', fontWeight: 700, marginBottom: '0.4rem' }}>
                Verbatim Cited Quote
              </div>
              <blockquote
                style={{
                  background: '#f8fafc',
                  padding: '1rem',
                  borderRadius: '8px',
                  borderLeft: '4px solid #0f766e',
                  color: '#1e293b',
                  fontSize: '0.95rem',
                  lineHeight: 1.65,
                  fontStyle: 'italic',
                  border: '1px solid #e2e8f0',
                  borderLeftWidth: '4px',
                  borderLeftColor: '#0f766e',
                }}
              >
                "{citation.exact_quote}"
              </blockquote>
            </div>
          )}

          {/* Metadata Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '1rem',
              background: '#f8fafc',
              padding: '1rem',
              borderRadius: '8px',
              border: '1px solid #e2e8f0',
            }}
          >
            <div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Section</div>
              <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#0f172a', marginTop: '0.2rem' }}>
                {citation.item_section || 'N/A'}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>CIK</div>
              <div style={{ fontSize: '0.88rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#0f172a', marginTop: '0.2rem' }}>
                {citation.cik || 'N/A'}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Accession Number</div>
              <div style={{ fontSize: '0.88rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#0f766e', marginTop: '0.2rem' }}>
                {citation.accession_number || 'N/A'}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>XBRL Concept Tag</div>
              <div style={{ fontSize: '0.88rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#0284c7', marginTop: '0.2rem' }}>
                {citation.xbrl_tag || 'Non-numeric Text'}
              </div>
            </div>
          </div>

          {/* SEC Archive Link */}
          {edgarUrl && (
            <div style={{ marginTop: '0.5rem' }}>
              <a
                href={edgarUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  background: '#0f766e',
                  border: '1px solid #115e59',
                  color: '#ffffff',
                  padding: '0.65rem 1.15rem',
                  borderRadius: '8px',
                  textDecoration: 'none',
                  fontSize: '0.88rem',
                  fontWeight: 600,
                  transition: 'all 0.2s',
                  boxShadow: '0 2px 8px rgba(15, 118, 110, 0.25)',
                }}
              >
                <span>View Official Filing on SEC EDGAR</span>
                <ExternalLink size={15} />
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
