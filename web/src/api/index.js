const API_BASE = ''

function authHeaders() {
  const h = {}
  const ck = sessionStorage.getItem('cloudKey')
  if (ck) h['x-cloud-key'] = ck
  return h
}

async function request(method, path, opts = {}) {
  const { body, headers = {}, params } = opts
  let url = `${API_BASE}${path}`
  if (params) {
    const qs = new URLSearchParams(params).toString()
    if (qs) url += '?' + qs
  }
  const res = await fetch(url, {
    method,
    headers: { ...authHeaders(), ...headers },
    credentials: 'include',
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status}`)
    err.status = res.status
    throw err
  }
  return res
}

export function fetchModels(showCloud) {
  const params = showCloud ? { cloud: '1' } : {}
  const headers = {}
  const cloudKey = sessionStorage.getItem('cloudKey')
  if (showCloud && cloudKey) headers['x-cloud-key'] = cloudKey
  return request('GET', '/models', { params, headers }).then(r => r.json())
}

export function sendChatMessage(model, message, conversationId, cloudKey, image) {
  const headers = { 'Content-Type': 'application/json' }
  if (cloudKey) headers['x-cloud-key'] = cloudKey
  const body = { message, model }
  if (conversationId) body.conversation_id = conversationId
  if (image) body.image = image
  return request('POST', '/chat', { body, headers })
  // Caller: resp.headers.get('X-Conversation-Id') + resp.body
}

export function authCloud(key) {
  return request('POST', '/auth/cloud', {
    body: { key },
    headers: { 'Content-Type': 'application/json' },
  })
}

export function fetchConversations(limit) {
  const params = {}
  if (limit) params.limit = limit
  return request('GET', '/api/conversations', { params }).then(r => r.json())
}

export function fetchConversation(id) {
  return request('GET', `/api/conversations/${id}`).then(r => r.json())
}

export function fetchUsage() {
  return request('GET', '/api/stats/usage').then(r => r.json())
}

// ── Multi-session management ──

export function apiCreateConversation(modelId) {
  return request('POST', '/api/conversations', {
    body: { model_id: modelId },
    headers: { 'Content-Type': 'application/json' },
  }).then(r => r.json())
}

export function apiUpdateConversation(id, title) {
  return request('PATCH', `/api/conversations/${id}`, {
    body: { title },
    headers: { 'Content-Type': 'application/json' },
  }).then(r => r.json())
}

export function apiDeleteConversation(id) {
  return request('DELETE', `/api/conversations/${id}`)
    .then(r => r.json())
}

// ── Auth Gate ──

export function apiRegister(username, password, security_question, security_answer) {
  return request('POST', '/api/auth/register', {
    body: { username, password, security_question, security_answer },
    headers: { 'Content-Type': 'application/json' },
  }).then(r => r.json())
}

export function apiLogin(username, password) {
  return request('POST', '/api/auth/login', {
    body: { username, password },
    headers: { 'Content-Type': 'application/json' },
  }).then(r => r.json())
}

export function apiCaptcha() {
  return request('POST', '/api/auth/captcha').then(r => r.json())
}

export function verifyToken(username, token) {
  return request('POST', '/api/auth/verify', {
    body: { username, token },
    headers: { 'Content-Type': 'application/json' },
  }).then(r => r.json())
}

export function apiGetSecurity(username) {
  return request('POST', '/api/auth/security', {
    body: { username },
    headers: { 'Content-Type': 'application/json' },
  }).then(r => r.json())
}

export function apiVerifySecurity(username, answer) {
  return request('POST', '/api/auth/verify-security', {
    body: { username, answer },
    headers: { 'Content-Type': 'application/json' },
  }).then(r => r.json())
}

export function apiResetPassword(username, newPassword) {
  return request('POST', '/api/auth/reset-password', {
    body: { username, new_password: newPassword },
    headers: { 'Content-Type': 'application/json' },
  }).then(r => r.json())
}

export function checkUsername(username) {
  return request('POST', '/api/auth/check-username', {
    body: { username },
    headers: { 'Content-Type': 'application/json' },
  }).then(r => r.json())
}
