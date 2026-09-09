import React from 'react';

/**
 * BrandLogo — Official Concept C Vector Emblem for Filing Sleuth
 *
 * Minimalist Cyber Ledger Reticle:
 * Structured filing ledger sheet with binder perforations,
 * illuminated neon cyan reticle lens with 4 crosshair ticks,
 * and high-precision financial data focal points.
 */
export default function BrandLogo({
  size = 24,
  className = '',
  animated = true,
  variant = 'glow', // 'glow' | 'standard' | 'flat'
}) {
  return (
    <div
      className={`brand-logo-wrapper ${animated ? 'has-animation' : ''} ${className}`}
      style={{
        width: size,
        height: size,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        flexShrink: 0,
      }}
    >
      <svg
        viewBox="0 0 48 48"
        width={size}
        height={size}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="brand-logo-svg"
      >
        <defs>
          {/* Cyber Neon Cyan Glow Gradient */}
          <linearGradient id="conceptCCyanGrad" x1="8" y1="8" x2="40" y2="40" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="45%" stopColor="#22d3ee" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>

          {/* Ledger Sheet Stroke Gradient */}
          <linearGradient id="conceptCLedgerGrad" x1="10" y1="6" x2="38" y2="42" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#334155" />
            <stop offset="50%" stopColor="#1e293b" />
            <stop offset="100%" stopColor="#0f766e" />
          </linearGradient>

          {/* Glowing Lens Glass Gradient */}
          <radialGradient id="conceptCLensGlass" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.22" />
            <stop offset="70%" stopColor="#06b6d4" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#0891b2" stopOpacity="0.28" />
          </radialGradient>

          {/* Neon Reticle Glow Filter */}
          <filter id="conceptCGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="1.6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* 1. Background Filing Ledger Sheet */}
        <rect
          x="10.5"
          y="6.5"
          width="27"
          height="35"
          rx="3.5"
          fill="#0a0f1d"
          stroke="url(#conceptCLedgerGrad)"
          strokeWidth="1.8"
        />

        {/* 2. Left Spine Binder Perforations (Notebook / Filing Dossier notches) */}
        <line x1="8.5" y1="13" x2="11.5" y2="13" stroke="#22d3ee" strokeWidth="1.6" strokeLinecap="round" opacity="0.85" />
        <line x1="8.5" y1="20" x2="11.5" y2="20" stroke="#22d3ee" strokeWidth="1.6" strokeLinecap="round" opacity="0.85" />
        <line x1="8.5" y1="28" x2="11.5" y2="28" stroke="#22d3ee" strokeWidth="1.6" strokeLinecap="round" opacity="0.85" />
        <line x1="8.5" y1="35" x2="11.5" y2="35" stroke="#22d3ee" strokeWidth="1.6" strokeLinecap="round" opacity="0.85" />

        {/* 3. Internal Financial Ledger Statement Lines */}
        <line x1="16" y1="13" x2="28" y2="13" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" />
        <line x1="16" y1="18.5" x2="31" y2="18.5" stroke="#334155" strokeWidth="1.5" strokeLinecap="round" />
        <line x1="16" y1="24" x2="21" y2="24" stroke="#38bdf8" strokeWidth="1.6" strokeLinecap="round" opacity="0.9" />
        <line x1="23" y1="24" x2="32" y2="24" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" />
        <line x1="16" y1="29.5" x2="30" y2="29.5" stroke="#334155" strokeWidth="1.5" strokeLinecap="round" />
        <line x1="16" y1="35" x2="25" y2="35" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" />

        {/* 4. Illuminated Neon Cyan Reticle Lens (Concept C) */}
        <g filter="url(#conceptCGlow)">
          {/* Lens Glass Body */}
          <circle
            cx="24"
            cy="24"
            r="11.5"
            fill="url(#conceptCLensGlass)"
            stroke="url(#conceptCCyanGrad)"
            strokeWidth="2.2"
            className="radar-optic-ring"
          />

          {/* 4 Primary Reticle Crosshairs (Top, Bottom, Left, Right) */}
          <line x1="24" y1="8.5" x2="24" y2="13.5" stroke="#22d3ee" strokeWidth="2" strokeLinecap="round" />
          <line x1="24" y1="34.5" x2="24" y2="39.5" stroke="#22d3ee" strokeWidth="2" strokeLinecap="round" />
          <line x1="8.5" y1="24" x2="13.5" y2="24" stroke="#22d3ee" strokeWidth="2" strokeLinecap="round" />
          <line x1="34.5" y1="24" x2="39.5" y2="24" stroke="#22d3ee" strokeWidth="2" strokeLinecap="round" />

          {/* Focal Precision Dots inside Reticle */}
          <circle cx="24" cy="24" r="1.4" fill="#67e8f9" />

          {/* Sleek Ergonomic Magnifying Handle (Angled Bottom-Right) */}
          <line
            x1="32.5"
            y1="32.5"
            x2="41"
            y2="41"
            stroke="url(#conceptCCyanGrad)"
            strokeWidth="3.2"
            strokeLinecap="round"
          />
        </g>
      </svg>
    </div>
  );
}
