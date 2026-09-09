import React from 'react';

/**
 * BrandLogo — Official Vector Emblem for Filing Sleuth
 *
 * Blends an SEC 10-K filing document (folded corner & ledger rows)
 * with a forensic optic reticle (magnifying lens + radar crosshair target).
 */
export default function BrandLogo({
  size = 24,
  className = '',
  animated = true,
  variant = 'gradient', // 'gradient' | 'monochrome' | 'glow'
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
          {/* Main Oceanic Teal to Cyan Gradient */}
          <linearGradient id="fsTealCyanGrad" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#0f766e" />
            <stop offset="50%" stopColor="#0d9488" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>

          {/* Accent Gold / Emerald Glow Gradient */}
          <linearGradient id="fsRadarGrad" x1="16" y1="16" x2="38" y2="38" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#2dd4bf" />
            <stop offset="100%" stopColor="#38bdf8" />
          </linearGradient>

          {/* Folded Corner Triangle Gradient */}
          <linearGradient id="fsFoldGrad" x1="30" y1="4" x2="40" y2="14" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#14b8a6" />
            <stop offset="100%" stopColor="#0f766e" />
          </linearGradient>

          {/* Subtle Outer Drop Shadow */}
          <filter id="fsGlowFilter" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#06b6d4" floodOpacity="0.35" />
          </filter>
        </defs>

        {/* 1. Base Filing Document Outline with Folded Top-Right Corner */}
        <path
          d="M8 8C8 5.79086 9.79086 4 12 4H30L40 14V40C40 42.2091 38.2091 44 36 44H12C9.79086 44 8 42.2091 8 40V8Z"
          fill="#0f172a"
          stroke="url(#fsTealCyanGrad)"
          strokeWidth="2.5"
          strokeLinejoin="round"
        />

        {/* 2. Folded Page Corner */}
        <path
          d="M30 4V12C30 13.1046 30.8954 14 32 14H40"
          fill="url(#fsFoldGrad)"
          stroke="url(#fsTealCyanGrad)"
          strokeWidth="2.5"
          strokeLinejoin="round"
        />

        {/* 3. Internal Financial Ledger Lines */}
        <line x1="14" y1="12" x2="24" y2="12" stroke="#334155" strokeWidth="2" strokeLinecap="round" />
        <line x1="14" y1="18" x2="26" y2="18" stroke="#334155" strokeWidth="2" strokeLinecap="round" />
        <line x1="14" y1="24" x2="18" y2="24" stroke="#334155" strokeWidth="2" strokeLinecap="round" />
        <line x1="14" y1="36" x2="24" y2="36" stroke="#334155" strokeWidth="2" strokeLinecap="round" />

        {/* 4. Forensic Optic Ring (Magnifying Glass / Radar Lens) */}
        <g filter={variant === 'glow' ? 'url(#fsGlowFilter)' : undefined}>
          {/* Outer Lens Circle */}
          <circle
            cx="27"
            cy="27"
            r="11"
            fill="rgba(15, 118, 110, 0.25)"
            stroke="url(#fsRadarGrad)"
            strokeWidth="2.5"
            className="radar-optic-ring"
          />

          {/* Inner Concentric Target Ring */}
          <circle
            cx="27"
            cy="27"
            r="6"
            stroke="rgba(45, 212, 191, 0.6)"
            strokeWidth="1.5"
            strokeDasharray="2 2"
          />

          {/* Radar Crosshairs */}
          <line x1="27" y1="13" x2="27" y2="19" stroke="url(#fsRadarGrad)" strokeWidth="2" strokeLinecap="round" />
          <line x1="27" y1="35" x2="27" y2="41" stroke="url(#fsRadarGrad)" strokeWidth="2" strokeLinecap="round" />
          <line x1="13" y1="27" x2="19" y2="27" stroke="url(#fsRadarGrad)" strokeWidth="2" strokeLinecap="round" />
          <line x1="35" y1="27" x2="41" y2="27" stroke="url(#fsRadarGrad)" strokeWidth="2" strokeLinecap="round" />

          {/* Center Precision Focal Point */}
          <circle cx="27" cy="27" r="2" fill="#38bdf8" />

          {/* Forensic Lens Handle (Angled at bottom-left) */}
          <path
            d="M19.5 34.5L13 41"
            stroke="url(#fsTealCyanGrad)"
            strokeWidth="3.5"
            strokeLinecap="round"
          />
          <path
            d="M18.5 35.5L12 42"
            stroke="#0f766e"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </g>
      </svg>
    </div>
  );
}
