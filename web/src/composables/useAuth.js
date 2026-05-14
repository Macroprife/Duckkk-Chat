import { ref, computed } from 'vue'
import { verifyToken } from '@/api'

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
const _token = ref(safeGet('duck_auth_token') || '')

export function useAuth() {
  const authed = computed(() => !!_loggedIn.value && !!_token.value)
  const username = computed(() => _loggedIn.value || '')

  function setAuthed(user, token) {
    _loggedIn.value = user
    _token.value = token || ''
    safeSet('duck_auth_user', user)
    safeSet('duck_auth_token', token || '')
  }

  function clearAuth() {
    _loggedIn.value = ''
    _token.value = ''
    safeRemove('duck_auth_user')
    safeRemove('duck_auth_token')
  }

  async function checkSession() {
    if (!_loggedIn.value || !_token.value) return false
    try {
      const data = await verifyToken(_loggedIn.value, _token.value)
      if (!data.valid) clearAuth()
      return data.valid
    } catch {
      return true // network error = still show UI
    }
  }

  return { authed, username, setAuthed, clearAuth, checkSession }
}
