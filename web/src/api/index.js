const API_BASE = ''

async function request(method, path, opts = {}) {
  const { body, headers = {}, params } = opts
  let url = `${API_BASE}${path}`
  if (params) {
    const qs = new URLSearchParams(params).toString()
    if (qs) url += '?' + qs
  }
  const res = await fetch(url, {
    method,
    headers: { ...headers },
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

export function sendChatMessage(model, message, cloudKey) {
  const headers = { 'Content-Type': 'application/json' }
  if (cloudKey) headers['x-cloud-key'] = cloudKey
  return request('POST', '/chat', {
    body: { message, model },
    headers,
  }).then(r => r.body)
}

export function authCloud(key) {
  return request('POST', '/auth/cloud', {
    body: { key },
    headers: { 'Content-Type': 'application/json' },
  })
}

export function fetchConversations() {
  return request('GET', '/api/conversations').then(r => r.json())
}

export function fetchConversation(id) {
  return request('GET', `/api/conversations/${id}`).then(r => r.json())
}

export function fetchUsage() {
  return request('GET', '/api/stats/usage').then(r => r.json())
}
