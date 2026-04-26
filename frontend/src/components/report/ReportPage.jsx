import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft, ChevronDown, ExternalLink, Clock, BookOpen,
  TrendingUp, AlertCircle, CheckCircle2, Zap, ArrowRight,
} from 'lucide-react'
import { useStore } from '../../store/index.js'
import { ScoreBar, Badge, Card } from '../ui/index.jsx'

const LEVEL_LABELS = {
  no_knowledge: 'No Knowledge',
  surface_awareness: 'Surface Awareness',
  working_knowledge: 'Working Knowledge',
  proficient: 'Proficient',
  expert: 'Expert',
}

const SCORE_COLORS = ['', '#d96b6b', '#d9966b', '#d9c46b', '#80c870', '#5cb87a']
const TIER_COLOR = { must_have: 'amber', nice_to_have: 'blue', bonus: 'default' }

export default function ReportPage() {
  const { reportData, candidateName, setActiveView } = useStore()

  if (!reportData) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-4)', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
          No report data available.
        </p>
      </div>
    )
  }

  const { assessed_skills = [], skill_gaps = [], learning_plan, overall_match_percent, job_title } = reportData
  const plan = learning_plan

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>

      {/* ── Nav ── */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 10,
        padding: '0 40px', height: '56px',
        display: 'flex', alignItems: 'center', gap: '16px',
        background: 'rgba(14,14,14,0.92)', backdropFilter: 'blur(12px)',
        borderBottom: '1px solid var(--border)',
      }}>
        <button
          onClick={() => setActiveView('chat')}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            background: 'none', border: 'none', color: 'var(--text-3)',
            fontSize: '13px', cursor: 'pointer',
            fontFamily: 'var(--font-sans)', padding: '6px 0',
            transition: 'color 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--text)'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--text-3)'}
        >
          <ArrowLeft size={14} /> Back to chat
        </button>

        <div style={{ flex: 1 }} />

        <div style={{ textAlign: 'right' }}>
          <p style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text)', lineHeight: 1.2 }}>
            {candidateName}
          </p>
          <p style={{ fontSize: '11px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)' }}>
            {job_title}
          </p>
        </div>
      </div>

      {/* ── Content ── */}
      <div style={{ maxWidth: '860px', width: '100%', margin: '0 auto', padding: '48px 40px 80px' }}>

        {/* Title */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: '40px' }}>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-4)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '10px' }}>
            Assessment Report
          </p>
          <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 'clamp(28px, 4vw, 40px)', fontWeight: 400, color: 'var(--text)', lineHeight: 1.15, letterSpacing: '-0.01em', marginBottom: '10px' }}>
            {candidateName}'s Skills
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--text-3)' }}>for <em>{job_title}</em></p>
        </motion.div>

        {/* ── Stats row ── */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '40px' }}
        >
          <StatCard label="Match Score" value={`${overall_match_percent}%`} accent sub="vs requirements" />
          <StatCard label="Assessed" value={assessed_skills.length} sub="skills evaluated" />
          <StatCard label="Gaps Found" value={skill_gaps.length} sub="need development" amber={skill_gaps.length > 0} />
          <StatCard label="Est. Time" value={plan ? `${plan.total_estimated_weeks}w` : '—'} sub={plan ? `${plan.total_estimated_hours}h total` : ''} />
        </motion.div>

        {/* ── Executive summary ── */}
        {plan?.executive_summary && (
          <Section title="Summary" delay={0.1}>
            <div style={{
              padding: '20px 24px',
              background: 'var(--surface)', border: '1px solid var(--border)',
              borderLeft: '2px solid var(--amber)',
              borderRadius: '0 var(--r3) var(--r3) 0',
              fontSize: '14.5px', color: 'var(--text-2)', lineHeight: 1.75,
            }}>
              {plan.executive_summary}
            </div>
          </Section>
        )}

        {/* ── Skill results ── */}
        <Section title="Skill Assessment" delay={0.15}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '12px' }}>
            {assessed_skills.map((s, i) => (
              <SkillCard key={s.skill} skill={s} index={i} />
            ))}
          </div>
        </Section>

        {/* ── Learning Plan ── */}
        {plan && skill_gaps.length > 0 && (
          <>
            <Section title="Learning Plan" delay={0.2}>
              {/* Plan meta */}
              <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
                {[
                  { label: 'Total Hours', value: `${plan.total_estimated_hours}h` },
                  { label: 'Duration', value: `${plan.total_estimated_weeks} weeks` },
                  { label: 'Commitment', value: `${plan.commitment_hours_per_week}h/week` },
                ].map(m => (
                  <div key={m.label} style={{
                    padding: '10px 16px', background: 'var(--surface)',
                    border: '1px solid var(--border)', borderRadius: 'var(--r2)',
                  }}>
                    <p style={{ fontSize: '10px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '3px' }}>
                      {m.label}
                    </p>
                    <p style={{ fontSize: '20px', fontFamily: 'var(--font-serif)', color: 'var(--amber)', lineHeight: 1 }}>
                      {m.value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Quick wins */}
              {plan.quick_wins?.length > 0 && (
                <div style={{
                  padding: '16px 20px', marginBottom: '20px',
                  background: 'rgba(92,184,122,0.05)', border: '1px solid rgba(92,184,122,0.15)',
                  borderRadius: 'var(--r3)',
                }}>
                  <p style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--green)', fontFamily: 'var(--font-mono)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '10px' }}>
                    <Zap size={12} /> Quick wins
                  </p>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {plan.quick_wins.map(w => (
                      <span key={w} style={{
                        padding: '4px 12px', borderRadius: 'var(--r-full)',
                        background: 'rgba(92,184,122,0.1)', border: '1px solid rgba(92,184,122,0.2)',
                        fontSize: '12px', color: 'var(--green)', fontFamily: 'var(--font-mono)',
                      }}>
                        {w}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Sequence */}
              {plan.recommended_sequence?.length > 0 && (
                <div style={{ marginBottom: '24px' }}>
                  <p style={{ fontSize: '11px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '10px' }}>
                    Recommended order
                  </p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    {plan.recommended_sequence.map((s, i) => (
                      <React.Fragment key={s}>
                        {i > 0 && <ArrowRight size={12} color="var(--border-2)" />}
                        <div style={{
                          padding: '5px 12px', background: 'var(--surface)',
                          border: '1px solid var(--border)', borderRadius: 'var(--r2)',
                          fontSize: '12px', color: 'var(--text-2)', display: 'flex', alignItems: 'center', gap: '6px',
                        }}>
                          <span style={{ fontSize: '10px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)' }}>{i + 1}</span>
                          {s}
                        </div>
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              )}

              {/* Skill paths */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {plan.skill_paths?.map((path, i) => (
                  <SkillPath key={path.skill_name} path={path} index={i} />
                ))}
              </div>
            </Section>
          </>
        )}

        {skill_gaps.length === 0 && (
          <Section title="Outcome" delay={0.2}>
            <div style={{
              padding: '32px', textAlign: 'center',
              background: 'rgba(92,184,122,0.05)', border: '1px solid rgba(92,184,122,0.2)',
              borderRadius: 'var(--r3)',
            }}>
              <CheckCircle2 size={32} color="var(--green)" style={{ marginBottom: '12px' }} />
              <p style={{ fontSize: '16px', fontFamily: 'var(--font-serif)', color: 'var(--text)', marginBottom: '6px' }}>
                Strong candidate match
              </p>
              <p style={{ fontSize: '13px', color: 'var(--text-3)' }}>
                Assessed skills meet or exceed all job requirements.
              </p>
            </div>
          </Section>
        )}
      </div>
    </div>
  )
}

// ── Subcomponents ─────────────────────────────────────────────────

function Section({ title, children, delay = 0 }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      style={{ marginBottom: '44px' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '20px' }}>
        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '22px', fontWeight: 400, color: 'var(--text)', whiteSpace: 'nowrap' }}>
          {title}
        </h2>
        <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
      </div>
      {children}
    </motion.section>
  )
}

function StatCard({ label, value, sub, accent, amber }) {
  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--r3)', padding: '18px 20px',
      borderTop: `2px solid ${amber ? 'var(--amber)' : accent ? 'var(--amber)' : 'var(--border)'}`,
    }}>
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-4)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '8px' }}>
        {label}
      </p>
      <p style={{ fontFamily: 'var(--font-serif)', fontSize: '32px', color: accent || amber ? 'var(--amber)' : 'var(--text)', lineHeight: 1, marginBottom: '4px' }}>
        {value}
      </p>
      <p style={{ fontSize: '12px', color: 'var(--text-4)' }}>{sub}</p>
    </div>
  )
}

function SkillCard({ skill, index }) {
  const score = skill.assessed_score || 0
  const level = LEVEL_LABELS[skill.level] || skill.level
  const tierColor = TIER_COLOR[skill.tier] || 'default'
  const claimed = skill.claimed_level

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 'var(--r3)', padding: '16px 18px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px', gap: '8px' }}>
        <p style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)', lineHeight: 1.2 }}>
          {skill.skill}
        </p>
        <Badge color={tierColor}>{skill.tier?.replace('_', ' ')}</Badge>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
        <ScoreBar score={score} />
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: SCORE_COLORS[Math.round(score)], width: '28px', textAlign: 'right', flexShrink: 0 }}>
          {score}/5
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <p style={{ fontSize: '11px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)' }}>
          {level}
        </p>
        {claimed && (
          <p style={{ fontSize: '11px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)' }}>
            claimed: {claimed}/5
          </p>
        )}
      </div>

      {skill.evidence && (
        <p style={{ fontSize: '12px', color: 'var(--text-4)', lineHeight: 1.5, marginTop: '8px', borderTop: '1px solid var(--border)', paddingTop: '8px' }}>
          {skill.evidence.replace('SUMMARY: ', '')}
        </p>
      )}
    </motion.div>
  )
}

function SkillPath({ path, index }) {
  const [open, setOpen] = useState(index === 0)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r3)', overflow: 'hidden' }}
    >
      {/* Header */}
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: '100%', padding: '18px 20px',
          display: 'flex', alignItems: 'flex-start', gap: '16px',
          background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left',
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
        onMouseLeave={e => e.currentTarget.style.background = 'none'}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <p style={{ fontSize: '15px', fontWeight: 500, color: 'var(--text)' }}>
              {path.skill_name}
            </p>
            <div style={{
              padding: '1px 8px', background: 'var(--amber-glow)', border: '1px solid var(--amber-ring)',
              borderRadius: 'var(--r-full)', fontSize: '11px', color: 'var(--amber)',
              fontFamily: 'var(--font-mono)',
            }}>
              gap: {path.gap?.gap_size}
            </div>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-3)', lineHeight: 1.5 }}>
            {path.why_prioritised}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexShrink: 0 }}>
          <div style={{ textAlign: 'right' }}>
            <p style={{ fontFamily: 'var(--font-serif)', fontSize: '20px', color: 'var(--amber)', lineHeight: 1 }}>
              {path.estimated_hours}h
            </p>
            <p style={{ fontSize: '11px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)' }}>
              ~{path.estimated_weeks}w
            </p>
          </div>
          <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronDown size={16} color="var(--text-4)" />
          </motion.div>
        </div>
      </button>

      {/* Body */}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ padding: '0 20px 20px', borderTop: '1px solid var(--border)' }}>

              {/* Prerequisites */}
              {path.prerequisite_skills?.length > 0 && (
                <div style={{ marginTop: '16px', marginBottom: '12px' }}>
                  <p style={{ fontSize: '11px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '8px' }}>
                    Prerequisites
                  </p>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {path.prerequisite_skills.map(p => (
                      <span key={p} style={{ padding: '3px 10px', background: 'var(--surface-2)', border: '1px solid var(--border-2)', borderRadius: 'var(--r2)', fontSize: '12px', color: 'var(--text-3)' }}>
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Milestones */}
              {path.milestones?.length > 0 && (
                <div style={{ marginTop: '16px', marginBottom: '16px' }}>
                  <p style={{ fontSize: '11px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '10px' }}>
                    Milestones
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
                    {path.milestones.map((m, i) => (
                      <div key={i} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', padding: '7px 0' }}>
                        <div style={{ width: '1px', background: i === 0 ? 'var(--amber)' : 'var(--border-2)', alignSelf: 'stretch', flexShrink: 0, marginLeft: '5px', marginTop: '6px' }} />
                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: i === 0 ? 'var(--amber)' : 'var(--border-2)', flexShrink: 0, marginTop: '5px', marginLeft: '-4.5px' }} />
                        <p style={{ fontSize: '13.5px', color: 'var(--text-2)', lineHeight: 1.55 }}>{m}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Resources */}
              {path.resources?.length > 0 && (
                <div style={{ marginTop: '16px' }}>
                  <p style={{ fontSize: '11px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '10px' }}>
                    Resources
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {path.resources.map((r, i) => (
                      <ResourceCard key={i} resource={r} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

const RESOURCE_TYPE_COLORS = {
  course:        { bg: 'rgba(232,160,32,0.08)',   text: 'var(--amber)',  label: 'Course' },
  book:          { bg: 'rgba(107,159,217,0.08)',  text: 'var(--blue)',   label: 'Book' },
  video:         { bg: 'rgba(217,107,107,0.08)',  text: 'var(--red)',    label: 'Video' },
  article:       { bg: 'rgba(92,184,122,0.08)',   text: 'var(--green)',  label: 'Article' },
  documentation: { bg: 'rgba(92,184,122,0.08)',   text: 'var(--green)',  label: 'Docs' },
  project:       { bg: 'rgba(255,255,255,0.04)',  text: 'var(--text-3)', label: 'Project' },
  practice:      { bg: 'rgba(255,255,255,0.04)',  text: 'var(--text-3)', label: 'Practice' },
}

function ResourceCard({ resource: r }) {
  const type = RESOURCE_TYPE_COLORS[r.resource_type] || RESOURCE_TYPE_COLORS.article

  return (
    <a
      href={r.url} target="_blank" rel="noopener noreferrer"
      style={{
        display: 'flex', alignItems: 'flex-start', gap: '12px',
        padding: '12px 14px', background: 'var(--surface-2)',
        border: '1px solid var(--border)', borderRadius: 'var(--r2)',
        textDecoration: 'none', transition: 'border-color 0.15s',
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--amber)'}
      onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
    >
      <span style={{
        padding: '2px 8px', borderRadius: 'var(--r1)',
        background: type.bg, color: type.text,
        fontSize: '10px', fontFamily: 'var(--font-mono)', letterSpacing: '0.06em',
        textTransform: 'uppercase', flexShrink: 0, marginTop: '1px',
        whiteSpace: 'nowrap',
      }}>
        {type.label}
      </span>

      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: '13.5px', color: 'var(--text)', fontWeight: 500, marginBottom: '3px', lineHeight: 1.3 }}>
          {r.title}
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {r.platform && (
            <span style={{ fontSize: '11px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)' }}>
              {r.platform}
            </span>
          )}
          <span style={{ display: 'flex', alignItems: 'center', gap: '3px', fontSize: '11px', color: 'var(--text-4)', fontFamily: 'var(--font-mono)' }}>
            <Clock size={10} /> {r.estimated_hours}h
          </span>
          {r.is_free && (
            <span style={{ fontSize: '10px', color: 'var(--green)', background: 'rgba(92,184,122,0.1)', padding: '1px 6px', borderRadius: 'var(--r-full)', fontFamily: 'var(--font-mono)' }}>
              FREE
            </span>
          )}
        </div>
        {r.description && (
          <p style={{ fontSize: '12px', color: 'var(--text-4)', marginTop: '4px', lineHeight: 1.45 }}>
            {r.description}
          </p>
        )}
      </div>

      <ExternalLink size={13} color="var(--text-4)" style={{ flexShrink: 0, marginTop: '2px' }} />
    </a>
  )
}