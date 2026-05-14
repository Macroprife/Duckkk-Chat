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

// Token is now HttpOnly cookie (browser handles it automatically)
// We only track the logged-in username locally for UI purposes
const _loggedIn = ref(safeGet('duck_auth_user') || '')

export function useAuth() {
  const authed = computed(() => !!_loggedIn.value)
  const username = computed(() => _loggedIn.value || '')

  function setAuthed(user) {
    _loggedIn.value = user
    safeSet('duck_auth_user', user)
  }

  function clearAuth() {
    _loggedIn.value = ''
    safeRemove('duck_auth_user')
  }

  async function checkSession() {
    if (!_loggedIn.value) return false
    try {
      const { verifyToken } = await import('@/api')
      const data = await verifyToken(_loggedIn.value, '')
      if (!data.valid) clearAuth()
      return data.valid
    } catch {
      return true
    }
  }

  return { authed, username, setAuthed, clearAuth, checkSession }
}
