import React from 'react';

/**
 * BullLogo Component
 * Sleek, modern geometric fintech brandmark.
 * Inspired by top-tier modern fintech design (Stripe, Linear, Mercury).
 * Clean geometric angles, charging horns, and forward momentum.
 */
export default function BullLogo({ size = 32, className = '' }) {
  return (
    <div
      className={className}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="bullTealLinear" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2DD4BF" />
            <stop offset="50%" stopColor="#00A884" />
            <stop offset="100%" stopColor="#0D9488" />
          </linearGradient>
          <linearGradient id="hornAccentLinear" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#FCD34D" />
          </linearGradient>
          <linearGradient id="tileDarkLinear" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0F2830" />
            <stop offset="100%" stopColor="#08141B" />
          </linearGradient>
        </defs>

        {/* Squircle base with subtle inner glow and hairline border */}
        <rect
          x="1"
          y="1"
          width="38"
          height="38"
          rx="10"
          fill="url(#tileDarkLinear)"
          stroke="rgba(20, 184, 166, 0.3)"
          strokeWidth="1.2"
        />

        {/* Minimalist Geometric Bull Silhouette */}
        {/* Left Horn */}
        <path
          d="M 15 16 C 12 13 8 11 6 7 C 9 9 13 11 15 14 Z"
          fill="url(#hornAccentLinear)"
        />

        {/* Right Horn */}
        <path
          d="M 25 16 C 28 13 32 11 34 7 C 31 9 27 11 25 14 Z"
          fill="url(#hornAccentLinear)"
        />

        {/* Faceted Bull Brow & Forehead */}
        <polygon
          points="20,11 26,16 23,24 20,29 17,24 14,16"
          fill="url(#bullTealLinear)"
        />

        {/* Highlight facet for dimensional depth */}
        <polygon
          points="20,11 20,29 23,24 26,16"
          fill="#5EEAD4"
          opacity="0.35"
        />

        {/* Glowing core dot */}
        <circle cx="20" cy="20" r="1.5" fill="#FFFFFF" opacity="0.95" />
      </svg>
    </div>
  );
}
