import { ref, computed } from 'vue'

function safeGet(key) {
  try { return localStorage.getItem(key) } catch { return null }
}
function safeSet(key, val) {
  try { localStorage.setItem(key, val) } catch {}
}
function safeRemove(key) {
  try { localStorage.removeItem(key) } catch {}
}

const _loggedIn = ref(safeGet('duck_auth_user') || '')
const _role = ref(safeGet('duck_auth_role') || 'user')
const _token = ref(safeGet('duck_auth_token') || '')

export function useAuth() {
  const authed = computed(() => !!_loggedIn.value)
  const username = computed(() => _loggedIn.value || '')
  const role = computed(() => _role.value || 'user')
  const isAdmin = computed(() => _role.value === 'admin')

  function setAuthed(user, userRole, token) {
    _loggedIn.value = user
    _role.value = userRole || 'user'
    _token.value = token || ''
    safeSet('duck_auth_user', user)
    safeSet('duck_auth_role', userRole || 'user')
    if (token) safeSet('duck_auth_token', token)
  }

  function clearAuth() {
    _loggedIn.value = ''
    _role.value = 'user'
    _token.value = ''
    safeRemove('duck_auth_user')
    safeRemove('duck_auth_role')
    safeRemove('duck_auth_token')
  }

  async function checkSession() {
    if (!_loggedIn.value) return false
    try {
      const { verifyToken } = await import('@/api')
      const data = await verifyToken(_loggedIn.value, _token.value)
      if (!data.valid) clearAuth()
      return data.valid
    } catch {
      return _token.value ? false : true  // token exists but request failed → assume invalid
    }
  }

  return { authed, username, role, isAdmin, setAuthed, clearAuth, checkSession }
}
