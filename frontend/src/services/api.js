const BASE = '/api/v1/assessment'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  startSession: (jdText, resumeText, commitmentHoursPerWeek = 10) =>
    request('/sessions', {
      method: 'POST',
      body: JSON.stringify({
        jd_text: jdText,
        resume_text: resumeText,
        commitment_hours_per_week: commitmentHoursPerWeek,
      }),
    }),

  respond: (sessionId, message) =>
    request(`/sessions/${sessionId}/respond`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),

  getReport: (sessionId) =>
    request(`/sessions/${sessionId}/report`),

  getStatus: (sessionId) =>
    request(`/sessions/${sessionId}/status`),
}