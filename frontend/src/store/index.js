import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // Session
  sessionId: null,
  phase: 'idle', // idle | assessing | analysing | planning | complete | error
  candidateName: '',
  jobTitle: '',
  skills: [],
  progress: { total_skills: 0, completed_skills: 0, percent_complete: 0, current_skill: null },

  // Chat
  messages: [],
  isWaiting: false,

  // Report
  reportData: null,

  // UI
  activeView: 'setup', // setup | chat | report

  // ── Actions ──────────────────────────────────

  setActiveView: (view) => set({ activeView: view }),

  initSession: (data) => set({
    sessionId: data.session_id,
    candidateName: data.candidate_name || 'Candidate',
    skills: data.skills_to_assess || [],
    phase: data.phase,
    activeView: 'chat',
    messages: [],
    progress: { total_skills: (data.skills_to_assess || []).length, completed_skills: 0, percent_complete: 0, current_skill: data.skills_to_assess?.[0] || null },
  }),

  addMessage: (role, content) => set((s) => ({
    messages: [...s.messages, { id: Date.now() + Math.random(), role, content, ts: Date.now() }],
  })),

  setWaiting: (v) => set({ isWaiting: v }),

  updateProgress: (progress) => set((s) => ({
    progress: { ...s.progress, ...progress },
    phase: progress.phase || s.phase,
  })),

  setReport: (data) => set({ reportData: data, phase: 'complete' }),

  setJobTitle: (jobTitle) => set({ jobTitle }),

  reset: () => set({
    sessionId: null, phase: 'idle', candidateName: '', jobTitle: '',
    skills: [], messages: [], isWaiting: false, reportData: null,
    activeView: 'setup', progress: { total_skills: 0, completed_skills: 0, percent_complete: 0, current_skill: null },
  }),
}))