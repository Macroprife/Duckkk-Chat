import { ref, computed } from 'vue'
import { authCloud as apiAuthCloud } from '@/api'

const cloudKey = ref(sessionStorage.getItem('cloudKey') || '')
const isAuthed = computed(() => !!cloudKey.value)

export function useAuth() {
  async function login(key) {
    try {
      const r = await apiAuthCloud(key)
      if (r.status === 429) return { ok: false, msg: '尝试过于频繁，请稍后再试' }
      if (!r.ok) return { ok: false, msg: '密钥错误' }
      cloudKey.value = key
      sessionStorage.setItem('cloudKey', key)
      return { ok: true }
    } catch (e) {
      return { ok: false, msg: `验证失败: ${e.message}` }
    }
  }

  function logout() {
    cloudKey.value = ''
    sessionStorage.removeItem('cloudKey')
  }

  return { cloudKey, isAuthed, login, logout }
}
