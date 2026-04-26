const BASE = '/api/v1/assessment'
const REQUEST_TIMEOUT_MS = 30000

async function request(path, options = {}) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      signal: controller.signal,
      ...options,
    })
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Request timed out. Backend may be processing too long or unreachable.')
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
  }

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