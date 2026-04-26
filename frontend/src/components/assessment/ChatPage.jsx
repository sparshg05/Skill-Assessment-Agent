import React, { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, ChevronRight, CheckCircle2, Circle, Loader2, FileText } from 'lucide-react'
import { useStore } from '../../store/index.js'
import { api } from '../../services/api.js'
import { ProgressRing, ScoreBar } from '../ui/index.jsx'

export default function ChatPage() {
  const {
    sessionId, messages, skills, progress, phase,
    candidateName, jobTitle, isWaiting,
    addMessage, setWaiting, updateProgress, setReport, setActiveView,
  } = useStore()

  const [input, setInput] = useState('')
  const endRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isWaiting])

  useEffect(() => {
    if (!isWaiting) inputRef.current?.focus()
  }, [isWaiting])

  const send = useCallback(async () => {
    const text = input.trim()
    if (!text || isWaiting) return
    setInput('')
    addMessage('user', text)
    setWaiting(true)

    try {
      const data = await api.respond(sessionId, text)
      addMessage('assistant', data.bot_message)
      updateProgress(data.progress || {})

      if (data.is_complete) {
        try {
          const report = await api.getReport(sessionId)
          setReport(report)
        } catch (err) {
          addMessage('system', `Assessment finished, but report fetch failed: ${err.message}`)
        }
      }
    } catch (err) {
      addMessage('system', `Something went wrong: ${err.message}`)
    } finally {
      setWaiting(false)
    }
  }, [input, isWaiting, sessionId])

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  const isComplete = phase === 'complete'

  return (
    <div style={{ height: '100vh', display: 'flex', overflow: 'hidden' }}>

      {/* ── Sidebar ────────────────────────────────── */}
      <Sidebar skills={skills} progress={progress} candidateName={candidateName} jobTitle={jobTitle} />

      {/* ── Main chat ──────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>

        {/* Header */}
        <div style={{
          padding: '0 28px', height: '60px', display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', borderBottom: '1px solid var(--border)',
          flexShrink: 0, gap: '16px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', minWidth: 0 }}>
            <ProgressRing pct={progress.percent_complete || 0} size={36} stroke={2.5} />
            <div style={{ minWidth: 0 }}>
              <p style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)', lineHeight: 1.2 }}>
                {candidateName}
              </p>
              <p style={{
                fontSize: '11px', color: isComplete ? 'var(--green)' : 'var(--amber)',
                fontFamily: 'var(--font-mono)', letterSpacing: '0.06em',
                textTransform: 'uppercase', lineHeight: 1.2,
              }}>
                {isComplete ? '✓ Complete' : `Assessing · ${progress.percent_complete || 0}%`}
              </p>
            </div>
          </div>

          {isComplete && (
            <motion.button
              initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
              onClick={() => setActiveView('report')}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '8px 16px', background: 'var(--amber)', color: 'var(--ink)',
                border: 'none', borderRadius: 'var(--r2)',
                fontSize: '13px', fontWeight: 600, cursor: 'pointer',
                fontFamily: 'var(--font-sans)', whiteSpace: 'nowrap',
              }}
            >
              <FileText size={14} /> View Report
            </motion.button>
          )}
        </div>

        {/* Messages */}
        <div style={{
          flex: 1, overflowY: 'auto', padding: '28px 28px 8px',
          display: 'flex', flexDirection: 'column', gap: '4px',
        }}>
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
          </AnimatePresence>

          {/* Typing indicator */}
          <AnimatePresence>
            {isWaiting && (
              <motion.div
                key="typing"
                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                style={{ display: 'flex', alignItems: 'flex-end', gap: '10px', padding: '4px 0' }}
              >
                <BotAvatar />
                <div style={{
                  padding: '10px 16px', background: 'var(--surface)',
                  border: '1px solid var(--border)', borderRadius: '2px 12px 12px 12px',
                  display: 'flex', alignItems: 'center', gap: '5px',
                }}>
                  {[0, 0.15, 0.3].map((d, i) => (
                    <motion.div key={i}
                      style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--text-4)' }}
                      animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
                      transition={{ duration: 0.8, delay: d, repeat: Infinity }}
                    />
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div ref={endRef} />
        </div>

        {/* Input */}
        <div style={{
          padding: '16px 28px 24px', borderTop: '1px solid var(--border)',
          flexShrink: 0,
        }}>
          {isComplete ? (
            <CompletionBar onViewReport={() => setActiveView('report')} />
          ) : (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                disabled={isWaiting}
                placeholder="Type your answer… (Enter to send, Shift+Enter for new line)"
                rows={1}
                style={{
                  flex: 1, background: 'var(--surface)', color: 'var(--text)',
                  border: '1px solid var(--border-2)', borderRadius: 'var(--r3)',
                  padding: '12px 16px', fontSize: '14px', lineHeight: 1.55,
                  resize: 'none', outline: 'none', fontFamily: 'var(--font-sans)',
                  transition: 'border-color 0.15s, box-shadow 0.15s',
                  maxHeight: '120px', overflowY: 'auto',
                  opacity: isWaiting ? 0.5 : 1,
                }}
                onFocus={e => {
                  e.target.style.borderColor = 'var(--amber)'
                  e.target.style.boxShadow = '0 0 0 3px var(--amber-ring)'
                }}
                onBlur={e => {
                  e.target.style.borderColor = 'var(--border-2)'
                  e.target.style.boxShadow = 'none'
                }}
                onInput={e => {
                  e.target.style.height = 'auto'
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
                }}
              />
              <motion.button
                onClick={send}
                disabled={!input.trim() || isWaiting}
                whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.95 }}
                style={{
                  width: 44, height: 44, borderRadius: 'var(--r2)',
                  background: input.trim() && !isWaiting ? 'var(--amber)' : 'var(--surface-2)',
                  border: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: input.trim() && !isWaiting ? 'var(--ink)' : 'var(--text-4)',
                  transition: 'background 0.15s, color 0.15s',
                  cursor: !input.trim() || isWaiting ? 'not-allowed' : 'pointer',
                  flexShrink: 0,
                }}
              >
                {isWaiting ? <Loader2 size={16} style={{ animation: 'spin 0.8s linear infinite' }} /> : <Send size={16} />}
              </motion.button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Message Bubble ────────────────────────────────────────────────
function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  const isSystem = msg.role === 'system'

  if (isSystem) {
    return (
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        style={{ alignSelf: 'center', margin: '8px 0' }}
      >
        <span style={{
          fontSize: '12px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)',
          background: 'var(--surface-2)', padding: '4px 12px', borderRadius: 'var(--r-full)',
        }}>
          {msg.content}
        </span>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      style={{
        display: 'flex', alignItems: 'flex-end', gap: '10px',
        flexDirection: isUser ? 'row-reverse' : 'row',
        padding: '4px 0', maxWidth: '100%',
      }}
    >
      {!isUser && <BotAvatar />}

      <div style={{
        maxWidth: 'min(580px, 75%)',
        padding: '12px 16px',
        background: isUser ? 'var(--amber)' : 'var(--surface)',
        color: isUser ? 'var(--ink)' : 'var(--text)',
        border: isUser ? 'none' : '1px solid var(--border)',
        borderRadius: isUser ? '12px 2px 12px 12px' : '2px 12px 12px 12px',
        fontSize: '14px', lineHeight: 1.65,
        whiteSpace: 'pre-wrap', wordBreak: 'break-word',
      }}>
        {msg.content}
      </div>
    </motion.div>
  )
}

function BotAvatar() {
  return (
    <div style={{
      width: 30, height: 30, borderRadius: '8px',
      background: 'var(--surface-2)', border: '1px solid var(--border-2)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
    }}>
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <rect x="1" y="1" width="5" height="5" rx="1" fill="var(--amber)" />
        <rect x="8" y="1" width="5" height="5" rx="1" fill="var(--amber)" opacity="0.4" />
        <rect x="1" y="8" width="5" height="5" rx="1" fill="var(--amber)" opacity="0.4" />
        <rect x="8" y="8" width="5" height="5" rx="1" fill="var(--amber)" />
      </svg>
    </div>
  )
}

// ── Sidebar ───────────────────────────────────────────────────────
function Sidebar({ skills, progress, candidateName, jobTitle }) {
  return (
    <div style={{
      width: '240px', flexShrink: 0,
      background: 'var(--surface)', borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Logo */}
      <div style={{ padding: '18px 20px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <div style={{
            width: '22px', height: '22px', background: 'var(--amber)',
            borderRadius: '5px', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="1" width="5" height="5" rx="1" fill="var(--ink)" />
              <rect x="8" y="1" width="5" height="5" rx="1" fill="var(--ink)" opacity="0.4" />
              <rect x="1" y="8" width="5" height="5" rx="1" fill="var(--ink)" opacity="0.4" />
              <rect x="8" y="8" width="5" height="5" rx="1" fill="var(--ink)" />
            </svg>
          </div>
          <span style={{ fontFamily: 'var(--font-serif)', fontSize: '15px', color: 'var(--text)' }}>SkillProbe</span>
        </div>
        {jobTitle && (
          <p style={{
            fontSize: '11px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)',
            letterSpacing: '0.03em', marginTop: '6px',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {jobTitle}
          </p>
        )}
      </div>

      {/* Skills list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 12px' }}>
        <p style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-4)',
          letterSpacing: '0.1em', textTransform: 'uppercase',
          marginBottom: '10px', paddingLeft: '8px',
        }}>
          Skills · {skills.length}
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {skills.map((skill, i) => {
            const completed = i < (progress.completed_skills || 0)
            const active = skill === progress.current_skill

            return (
              <motion.div
                key={skill}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '7px 8px', borderRadius: 'var(--r2)',
                  background: active ? 'var(--amber-glow)' : 'transparent',
                  border: `1px solid ${active ? 'var(--amber-ring)' : 'transparent'}`,
                  transition: 'all 0.2s',
                }}
              >
                {completed ? (
                  <CheckCircle2 size={13} color="var(--green)" strokeWidth={2} />
                ) : active ? (
                  <motion.div
                    animate={{ scale: [1, 1.3, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  >
                    <Circle size={13} color="var(--amber)" strokeWidth={2} />
                  </motion.div>
                ) : (
                  <Circle size={13} color="var(--border-2)" strokeWidth={1.5} />
                )}
                <span style={{
                  fontSize: '13px',
                  color: completed ? 'var(--text-4)' : active ? 'var(--text)' : 'var(--text-3)',
                  flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  textDecoration: completed ? 'line-through' : 'none',
                }}>
                  {skill}
                </span>
              </motion.div>
            )
          })}
        </div>
      </div>

      {/* Progress footer */}
      <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)' }}>
            Progress
          </span>
          <span style={{ fontSize: '11px', color: 'var(--amber)', fontFamily: 'var(--font-mono)' }}>
            {progress.percent_complete || 0}%
          </span>
        </div>
        <div style={{ height: '3px', background: 'var(--border)', borderRadius: '2px', overflow: 'hidden' }}>
          <motion.div
            style={{ height: '100%', background: 'var(--amber)', borderRadius: '2px' }}
            animate={{ width: `${progress.percent_complete || 0}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          />
        </div>
      </div>
    </div>
  )
}

// ── Completion Bar ────────────────────────────────────────────────
function CompletionBar({ onViewReport }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 20px',
        background: 'rgba(92,184,122,0.06)', border: '1px solid rgba(92,184,122,0.2)',
        borderRadius: 'var(--r3)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <CheckCircle2 size={18} color="var(--green)" />
        <div>
          <p style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text)', lineHeight: 1.2 }}>
            Assessment complete
          </p>
          <p style={{ fontSize: '12px', color: 'var(--text-4)', lineHeight: 1.2 }}>
            Your personalised learning plan is ready
          </p>
        </div>
      </div>
      <motion.button
        whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
        onClick={onViewReport}
        style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          padding: '9px 18px', background: 'var(--amber)', color: 'var(--ink)',
          border: 'none', borderRadius: 'var(--r2)',
          fontSize: '13px', fontWeight: 600, cursor: 'pointer',
          fontFamily: 'var(--font-sans)',
        }}
      >
        View Report <ChevronRight size={14} />
      </motion.button>
    </motion.div>
  )
}