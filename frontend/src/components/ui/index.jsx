import React from 'react'
import { motion } from 'framer-motion'

// ── Button ────────────────────────────────────────────────────────
export function Button({ children, variant = 'primary', size = 'md', disabled, loading, onClick, className = '', ...props }) {
  const base = {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    gap: '8px', fontFamily: 'var(--font-sans)', fontWeight: 500,
    border: 'none', borderRadius: 'var(--r2)', cursor: disabled || loading ? 'not-allowed' : 'pointer',
    transition: 'all 0.18s var(--ease)', letterSpacing: '0.01em',
    whiteSpace: 'nowrap', userSelect: 'none',
    opacity: disabled || loading ? 0.45 : 1,
  }
  const variants = {
    primary: {
      background: 'var(--amber)', color: 'var(--ink)',
      padding: size === 'sm' ? '8px 16px' : size === 'lg' ? '16px 32px' : '11px 22px',
      fontSize: size === 'sm' ? '13px' : size === 'lg' ? '15px' : '14px',
    },
    ghost: {
      background: 'transparent', color: 'var(--text-2)',
      border: '1px solid var(--border-2)',
      padding: size === 'sm' ? '7px 15px' : size === 'lg' ? '15px 31px' : '10px 21px',
      fontSize: size === 'sm' ? '13px' : size === 'lg' ? '15px' : '14px',
    },
    subtle: {
      background: 'var(--surface-2)', color: 'var(--text-2)',
      padding: size === 'sm' ? '7px 14px' : '10px 18px',
      fontSize: '13px',
    },
  }
  return (
    <motion.button
      style={{ ...base, ...variants[variant] }}
      whileHover={!disabled && !loading ? { scale: 1.02, filter: 'brightness(1.08)' } : {}}
      whileTap={!disabled && !loading ? { scale: 0.97 } : {}}
      onClick={!disabled && !loading ? onClick : undefined}
      {...props}
    >
      {loading ? <Spinner size={14} /> : children}
    </motion.button>
  )
}

// ── Spinner ───────────────────────────────────────────────────────
export function Spinner({ size = 18, color = 'currentColor' }) {
  return (
    <motion.svg
      width={size} height={size} viewBox="0 0 24 24" fill="none"
      animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
    >
      <circle cx="12" cy="12" r="9" stroke={color} strokeOpacity="0.2" strokeWidth="2.5" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
    </motion.svg>
  )
}

// ── Badge ─────────────────────────────────────────────────────────
export function Badge({ children, color = 'default' }) {
  const colors = {
    default: { bg: 'var(--surface-2)', text: 'var(--text-3)', border: 'var(--border-2)' },
    amber:   { bg: 'rgba(232,160,32,0.1)', text: 'var(--amber)', border: 'rgba(232,160,32,0.2)' },
    green:   { bg: 'rgba(92,184,122,0.1)', text: 'var(--green)', border: 'rgba(92,184,122,0.2)' },
    red:     { bg: 'rgba(217,107,107,0.1)', text: 'var(--red)', border: 'rgba(217,107,107,0.2)' },
    blue:    { bg: 'rgba(107,159,217,0.1)', text: 'var(--blue)', border: 'rgba(107,159,217,0.2)' },
  }
  const c = colors[color] || colors.default
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      padding: '2px 8px', borderRadius: 'var(--r-full)',
      fontSize: '11px', fontFamily: 'var(--font-mono)', letterSpacing: '0.04em',
      background: c.bg, color: c.text, border: `1px solid ${c.border}`,
    }}>
      {children}
    </span>
  )
}

// ── Card ──────────────────────────────────────────────────────────
export function Card({ children, style, ...props }) {
  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--r3)', ...style,
    }} {...props}>
      {children}
    </div>
  )
}

// ── Divider ───────────────────────────────────────────────────────
export function Divider({ style }) {
  return <div style={{ height: '1px', background: 'var(--border)', ...style }} />
}

// ── ScoreBar ──────────────────────────────────────────────────────
export function ScoreBar({ score, max = 5, animate: shouldAnimate = true }) {
  const pct = (score / max) * 100
  const colors = ['', '#d96b6b', '#d9966b', '#d9c46b', '#80c870', '#5cb87a']
  return (
    <div style={{ height: '4px', background: 'var(--border-2)', borderRadius: '2px', overflow: 'hidden', flex: 1 }}>
      <motion.div
        style={{ height: '100%', background: colors[Math.round(score)] || colors[3], borderRadius: '2px' }}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.8, ease: 'easeOut', delay: 0.1 }}
      />
    </div>
  )
}

// ── ProgressRing ──────────────────────────────────────────────────
export function ProgressRing({ pct = 0, size = 48, stroke = 3 }) {
  const r = (size - stroke * 2) / 2
  const circ = 2 * Math.PI * r
  const offset = circ - (pct / 100) * circ
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--border-2)" strokeWidth={stroke} />
      <motion.circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke="var(--amber)" strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circ}
        initial={{ strokeDashoffset: circ }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 1, ease: 'easeOut' }}
      />
    </svg>
  )
}

// ── Tooltip ───────────────────────────────────────────────────────
export function Tooltip({ children, label }) {
  const [show, setShow] = React.useState(false)
  return (
    <div style={{ position: 'relative', display: 'inline-flex' }}
      onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      {children}
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
          style={{
            position: 'absolute', bottom: 'calc(100% + 6px)', left: '50%',
            transform: 'translateX(-50%)',
            background: 'var(--fog)', color: 'var(--text)',
            padding: '4px 10px', borderRadius: 'var(--r1)',
            fontSize: '12px', whiteSpace: 'nowrap', pointerEvents: 'none',
            fontFamily: 'var(--font-mono)', zIndex: 100,
          }}
        >
          {label}
        </motion.div>
      )}
    </div>
  )
}