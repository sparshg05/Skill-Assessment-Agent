import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, Zap, BarChart2, Map } from 'lucide-react'
import { Button, Spinner } from '../ui/index.jsx'
import { api } from '../../services/api.js'
import { useStore } from '../../store/index.js'

const SAMPLE_JD = `Senior Backend Engineer — FinTech Platform

We're building the next generation of financial infrastructure and need a strong backend engineer to join our core platform team.

Required:
- 4+ years Python (FastAPI or Django preferred)
- Strong SQL and PostgreSQL experience
- Docker and container orchestration (Kubernetes)
- RESTful API design and best practices
- Experience with message queues (Redis, RabbitMQ, or Kafka)
- Understanding of distributed systems

Nice to have:
- AWS or GCP cloud services
- System design experience
- Knowledge of async Python (asyncio)`

const SAMPLE_RESUME = `Alex Chen
Senior Software Engineer | alex@example.com

EXPERIENCE
Backend Engineer — TechCorp (3 years)
Built and maintained REST APIs using Python and Flask. Worked with PostgreSQL databases. Some experience with Docker for local development. Used Redis for caching.

Junior Developer — StartupXYZ (1.5 years)  
Full-stack development with Python Django and React. Deployed on AWS EC2.

SKILLS
Languages: Python, JavaScript, SQL
Frameworks: Django, Flask, React
Tools: Git, Docker (basic), PostgreSQL, Redis
Cloud: Some AWS exposure

EDUCATION
B.S. Computer Science — State University`

export default function SetupPage() {
  const [jd, setJd] = useState('')
  const [resume, setResume] = useState('')
  const [commitment, setCommitment] = useState(10)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [usedSample, setUsedSample] = useState(false)

  const { initSession, addMessage, setJobTitle } = useStore()

  const handleStart = async () => {
    if (!jd.trim() || !resume.trim()) {
      setError('Please provide both the job description and resume.')
      return
    }
    setError('')
    setLoading(true)
    try {
      const data = await api.startSession(jd.trim(), resume.trim(), commitment)
      initSession(data)
      addMessage('assistant', data.message)
      // Extract job title hint for header
      const firstLine = jd.split('\n')[0].trim()
      setJobTitle(firstLine.length < 60 ? firstLine : 'Assessment')
    } catch (err) {
      setError(err.message || 'Failed to start session. Check backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const loadSample = () => {
    setJd(SAMPLE_JD)
    setResume(SAMPLE_RESUME)
    setUsedSample(true)
    setError('')
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>

      {/* ── Top bar ── */}
      <header style={{
        padding: '20px 32px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', borderBottom: '1px solid var(--border)',
      }}>
        <Wordmark />
        <button
          onClick={loadSample}
          style={{
            background: 'none', border: '1px solid var(--border-2)',
            color: 'var(--text-3)', borderRadius: 'var(--r2)',
            padding: '7px 14px', fontSize: '12px', fontFamily: 'var(--font-mono)',
            cursor: 'pointer', letterSpacing: '0.04em',
            transition: 'all 0.15s',
          }}
          onMouseEnter={e => { e.target.style.borderColor = 'var(--amber)'; e.target.style.color = 'var(--amber)' }}
          onMouseLeave={e => { e.target.style.borderColor = 'var(--border-2)'; e.target.style.color = 'var(--text-3)' }}
        >
          {usedSample ? '✓ sample loaded' : 'load sample'}
        </button>
      </header>

      {/* ── Hero ── */}
      <div style={{ padding: '64px 32px 48px', maxWidth: '640px' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <p style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px', letterSpacing: '0.12em',
            color: 'var(--amber)', textTransform: 'uppercase', marginBottom: '16px',
          }}>
            Skill Assessment Agent
          </p>
          <h1 style={{
            fontFamily: 'var(--font-serif)', fontSize: 'clamp(36px, 5vw, 52px)',
            fontWeight: 400, lineHeight: 1.1, color: 'var(--text)',
            marginBottom: '18px', letterSpacing: '-0.01em',
          }}>
            Resumes tell you what<br />
            <em style={{ color: 'var(--amber)' }}>someone claims</em> to know.
          </h1>
          <p style={{ fontSize: '15px', color: 'var(--text-3)', lineHeight: 1.7, maxWidth: '480px' }}>
            This agent has a real conversation with the candidate, tests each
            skill through adaptive questions, then builds a personalised
            learning plan for the gaps it finds.
          </p>
        </motion.div>

        {/* ── Feature pills ── */}
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.4 }}
          style={{ display: 'flex', gap: '10px', marginTop: '28px', flexWrap: 'wrap' }}
        >
          {[
            { icon: <Zap size={12} />, label: 'Adaptive Q&A' },
            { icon: <BarChart2 size={12} />, label: 'Proficiency scoring' },
            { icon: <Map size={12} />, label: 'Learning roadmap' },
          ].map(f => (
            <div key={f.label} style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '5px 12px', borderRadius: 'var(--r-full)',
              background: 'var(--surface)', border: '1px solid var(--border-2)',
              fontSize: '12px', color: 'var(--text-3)',
            }}>
              <span style={{ color: 'var(--amber)' }}>{f.icon}</span>
              {f.label}
            </div>
          ))}
        </motion.div>
      </div>

      {/* ── Form ── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        style={{ flex: 1, padding: '0 32px 48px' }}
      >
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', maxWidth: '900px', marginBottom: '20px' }}>
          <TextArea
            label="Job Description"
            placeholder={`Paste the job description here…\n\nInclude required skills, nice-to-haves, and any experience requirements.`}
            value={jd}
            onChange={setJd}
          />
          <TextArea
            label="Candidate Resume"
            placeholder={`Paste the resume here…\n\nInclude work history, skills, and any relevant experience.`}
            value={resume}
            onChange={setResume}
          />
        </div>

        {/* Commitment + CTA row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', maxWidth: '900px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)', letterSpacing: '0.06em' }}>
              WEEKLY COMMITMENT
            </span>
            <select
              value={commitment}
              onChange={e => setCommitment(Number(e.target.value))}
              style={{
                background: 'var(--surface)', border: '1px solid var(--border-2)',
                color: 'var(--text-2)', borderRadius: 'var(--r2)',
                padding: '7px 12px', fontSize: '13px',
                fontFamily: 'var(--font-mono)', cursor: 'pointer',
                outline: 'none',
              }}
            >
              {[5, 10, 15, 20].map(h => (
                <option key={h} value={h}>{h}h / week</option>
              ))}
            </select>
          </div>

          <Button
            variant="primary" size="lg"
            loading={loading} disabled={loading}
            onClick={handleStart}
            style={{ marginLeft: 'auto' }}
          >
            {!loading && <>Start Assessment <ArrowRight size={16} /></>}
          </Button>
        </div>

        <AnimatePresence>
          {error && (
            <motion.p
              initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              style={{
                marginTop: '14px', fontSize: '13px', color: 'var(--red)',
                background: 'rgba(217,107,107,0.08)', border: '1px solid rgba(217,107,107,0.2)',
                padding: '10px 14px', borderRadius: 'var(--r2)', maxWidth: '900px',
              }}
            >
              {error}
            </motion.p>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}

function TextArea({ label, placeholder, value, onChange }) {
  const [focused, setFocused] = React.useState(false)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <label style={{
        fontFamily: 'var(--font-mono)', fontSize: '11px', letterSpacing: '0.1em',
        textTransform: 'uppercase', color: focused ? 'var(--amber)' : 'var(--text-4)',
        transition: 'color 0.15s',
      }}>
        {label}
      </label>
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        rows={12}
        style={{
          background: 'var(--surface)', color: 'var(--text)',
          border: `1px solid ${focused ? 'var(--amber)' : 'var(--border)'}`,
          borderRadius: 'var(--r3)', padding: '14px 16px',
          fontSize: '13.5px', lineHeight: 1.65, resize: 'vertical',
          outline: 'none', transition: 'border-color 0.15s, box-shadow 0.15s',
          boxShadow: focused ? '0 0 0 3px var(--amber-ring)' : 'none',
          fontFamily: 'var(--font-sans)',
        }}
      />
    </div>
  )
}

function Wordmark() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <div style={{
        width: '28px', height: '28px', background: 'var(--amber)',
        borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <rect x="1" y="1" width="5" height="5" rx="1" fill="var(--ink)" />
          <rect x="8" y="1" width="5" height="5" rx="1" fill="var(--ink)" opacity="0.4" />
          <rect x="1" y="8" width="5" height="5" rx="1" fill="var(--ink)" opacity="0.4" />
          <rect x="8" y="8" width="5" height="5" rx="1" fill="var(--ink)" />
        </svg>
      </div>
      <span style={{ fontFamily: 'var(--font-serif)', fontSize: '18px', color: 'var(--text)', letterSpacing: '-0.01em' }}>
        SkillProbe
      </span>
    </div>
  )
}