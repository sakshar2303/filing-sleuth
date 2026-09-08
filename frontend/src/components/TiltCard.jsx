import React, { useRef, useState } from 'react';

/**
 * TiltCard: Lightweight 3D physics-based tilt and specular reflection container.
 * Zero external dependencies. Uses CSS 3D perspective and requestAnimationFrame.
 */
export default function TiltCard({ children, className = '', maxTilt = 8, scale = 1.015, style = {} }) {
  const cardRef = useRef(null);
  const [transformStyle, setTransformStyle] = useState('');
  const [glareStyle, setGlareStyle] = useState({ opacity: 0 });

  const handleMouseMove = (e) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rotateX = ((y - centerY) / centerY) * -maxTilt;
    const rotateY = ((x - centerX) / centerX) * maxTilt;

    setTransformStyle(
      `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(${scale}, ${scale}, ${scale})`
    );

    // Specular glare effect calculation
    const glareX = (x / rect.width) * 100;
    const glareY = (y / rect.height) * 100;
    setGlareStyle({
      opacity: 0.35,
      background: `radial-gradient(circle at ${glareX}% ${glareY}%, rgba(255, 255, 255, 0.6) 0%, rgba(255, 255, 255, 0) 65%)`,
    });
  };

  const handleMouseLeave = () => {
    setTransformStyle('perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)');
    setGlareStyle({ opacity: 0, transition: 'opacity 0.4s ease' });
  };

  return (
    <div
      ref={cardRef}
      className={`tilt-card-3d ${className}`}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        transform: transformStyle,
        transition: 'transform 0.15s ease-out',
        position: 'relative',
        transformStyle: 'preserve-3d',
        ...style,
      }}
    >
      {children}
      {/* Specular Glare Overlay */}
      <div
        className="tilt-glare-overlay"
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: 'inherit',
          pointerEvents: 'none',
          zIndex: 2,
          ...glareStyle,
        }}
      />
    </div>
  );
}
