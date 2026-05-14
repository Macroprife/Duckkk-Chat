<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md">
    <div class="w-full max-w-sm mx-4 fade-in">
      <div class="bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl">

        <div class="text-center mb-5">
          <span class="text-5xl block mb-2">🦆</span>
          <h1 class="text-lg font-semibold text-slate-100">Duck Chat</h1>
          <p class="text-xs text-slate-500 mt-1">{{ subtitle }}</p>
        </div>

        <!-- ===== LOGIN FORM ===== -->
        <form v-if="flow === 'login'" @submit.prevent="handleLogin" class="space-y-3">
          <div><input v-model="loginUser" class="input-field text-center" placeholder="用户名" autocomplete="username" autofocus /></div>
          <div class="relative">
            <input v-model="loginPass" :type="showLoginPw ? 'text' : 'password'" class="input-field text-center pr-10" placeholder="密码" autocomplete="current-password" />
            <button type="button" class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-sm" @click="showLoginPw = !showLoginPw">{{ showLoginPw ? '🙈' : '👁️' }}</button>
          </div>
          <p v-if="loginError" class="text-xs text-red-400 text-center whitespace-pre-wrap">{{ loginError }}</p>
          <button type="submit" class="btn-primary w-full" :disabled="loginLoading">{{ loginLoading ? '登录中...' : '登录' }}</button>
          <button type="button" class="btn-ghost w-full text-sm" @click="goRegister1">没有账号？注册</button>
          <button type="button" class="btn-ghost w-full text-xs text-slate-500" @click="goReset1">修改密码</button>
          <button type="button" class="btn-ghost w-full text-xs text-slate-600 hover:text-slate-400" @click="testConnection">检测连接</button>
        </form>

        <!-- ===== REGISTER: username + password ===== -->
        <form v-else-if="flow === 'register-1'" @submit.prevent="goRegister2" class="space-y-3">
          <div><input v-model="regUser" class="input-field text-center" placeholder="用户名（字母数字，≤8位）" maxlength="8" autocomplete="off" /></div>
          <div class="relative">
            <input v-model="regPass" :type="showRegPw ? 'text' : 'password'" class="input-field text-center pr-10" placeholder="密码（≥8位）" autocomplete="new-password" />
            <button type="button" class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-sm" @click="showRegPw = !showRegPw">{{ showRegPw ? '🙈' : '👁️' }}</button>
          </div>
          <p v-if="regError" class="text-xs text-red-400 text-center">{{ regError }}</p>
          <div class="flex gap-2 pt-1">
            <button type="button" class="btn-ghost flex-1" @click="flow='login';resetAll()">← 返回</button>
            <button type="submit" class="btn-primary flex-1">下一步</button>
          </div>
        </form>

        <!-- ===== REGISTER: security question ===== -->
        <form v-else-if="flow === 'register-2'" @submit.prevent="goRegister3" class="space-y-3">
          <div>
            <select v-model="secQuestion" class="input-field text-center">
              <option value="" disabled>请选择密保问题</option>
              <option value="你最喜欢的一首歌">你最喜欢的一首歌</option>
              <option value="你最喜欢的一部电影">你最喜欢的一部电影</option>
            </select>
          </div>
          <div><input v-model="secAnswer" class="input-field text-center" placeholder="自定义答案（区分大小写）" /></div>
          <p v-if="secError" class="text-xs text-red-400 text-center">{{ secError }}</p>
          <div class="flex gap-2 pt-1">
            <button type="button" class="btn-ghost flex-1" @click="flow='register-1';secError=''">← 上一步</button>
            <button type="submit" class="btn-primary flex-1">下一步</button>
          </div>
        </form>

        <!-- ===== CAPTCHA (shared: login + register) ===== -->
        <form v-else-if="flow === 'register-3' || flow === 'login-captcha'" @submit.prevent="handleCaptcha" class="space-y-3">
          <div class="text-center">
            <p class="text-sm text-slate-400 mb-2">{{ flow === 'register-3' ? '请完成人机验证以注册' : '验证通过，请完成人机验证' }}</p>
            <p class="text-2xl font-bold text-duck-300 my-3">{{ captchaQuestion }}</p>
            <input v-model="captchaAnswer" type="number" class="input-field text-center w-24 mx-auto" placeholder="?" autofocus />
            <p class="text-xs text-slate-500 mt-2">剩余尝试：{{ 3 - captchaAttempts }} 次</p>
          </div>
          <p v-if="captchaError" class="text-xs text-red-400 text-center">{{ captchaError }}</p>
          <div class="flex gap-2">
            <button type="button" class="btn-ghost flex-1" @click="cancelCaptcha">← 返回</button>
            <button type="submit" class="btn-primary flex-1" :disabled="captchaLoading">{{ captchaLoading ? '处理中...' : '确认' }}</button>
          </div>
        </form>

        <!-- ===== RESET: enter username ===== -->
        <form v-else-if="flow === 'reset-1'" @submit.prevent="checkResetUser" class="space-y-3">
          <div><input v-model="resetUser" class="input-field text-center" placeholder="输入要修改密码的账号" autocomplete="off" /></div>
          <p v-if="resetError" class="text-xs text-red-400 text-center">{{ resetError }}</p>
          <div class="flex gap-2 pt-1">
            <button type="button" class="btn-ghost flex-1" @click="flow='login';resetAll()">← 返回登录</button>
            <button type="submit" class="btn-primary flex-1">下一步</button>
          </div>
        </form>

        <!-- ===== RESET: answer security question ===== -->
        <form v-else-if="flow === 'reset-2'" @submit.prevent="checkSecurityAnswer" class="space-y-3">
          <div class="text-center">
            <p class="text-sm text-slate-400 mb-2">密保问题</p>
            <p class="text-base font-medium text-slate-200">{{ resetQuestion }}</p>
          </div>
          <div><input v-model="resetAnswer" class="input-field text-center" placeholder="输入答案（区分大小写）" /></div>
          <p v-if="resetError" class="text-xs text-red-400 text-center">{{ resetError }}</p>
          <p v-if="resetAttempts > 0" class="text-xs text-slate-500 text-center">剩余尝试：{{ 3 - resetAttempts }} 次</p>
          <div class="flex gap-2 pt-1">
            <button type="button" class="btn-ghost flex-1" @click="flow='login';resetAll()">← 返回登录</button>
            <button type="submit" class="btn-primary flex-1">下一步</button>
          </div>
        </form>

        <!-- ===== RESET: new password ===== -->
        <form v-else-if="flow === 'reset-3'" @submit.prevent="handleResetPassword" class="space-y-3">
          <div class="relative">
            <input v-model="resetNewPass" :type="showResetPw ? 'text' : 'password'" class="input-field text-center pr-10" placeholder="新密码（≥8位）" autocomplete="new-password" />
            <button type="button" class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-sm" @click="showResetPw = !showResetPw">{{ showResetPw ? '🙈' : '👁️' }}</button>
          </div>
          <p v-if="resetError" class="text-xs text-red-400 text-center">{{ resetError }}</p>
          <div class="flex gap-2 pt-1">
            <button type="button" class="btn-ghost flex-1" @click="flow='login';resetAll()">← 返回登录</button>
            <button type="submit" class="btn-primary flex-1" :disabled="resetLoading">{{ resetLoading ? '修改中...' : '确认修改' }}</button>
          </div>
        </form>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { apiRegister, apiLogin, apiCaptcha, apiGetSecurity, apiVerifySecurity, apiResetPassword, checkUsername } from '@/api'
import { useAuth } from '@/composables/useAuth'

const emit = defineEmits(['authed'])
const { setAuthed } = useAuth()

const showLoginPw = ref(false)
const showRegPw = ref(false)
const showResetPw = ref(false)

const flow = ref('login')

const subtitle = computed(() => {
  const m = {
    'login': '请登录或注册后使用',
    'register-1': '注册新账号',
    'register-2': '设置密保问题',
    'register-3': '人机验证',
    'reset-1': '修改密码',
    'reset-2': '验证密保',
    'reset-3': '设置新密码',
  }
  return m[flow.value] || ''
})

function resetAll() {
  loginUser.value = ''; loginPass.value = ''; loginError.value = ''
  regUser.value = ''; regPass.value = ''; regError.value = ''
  secQuestion.value = ''; secAnswer.value = ''; secError.value = ''
  resetUser.value = ''; resetAnswer.value = ''; resetNewPass.value = ''
  resetQuestion.value = ''; resetError.value = ''; resetAttempts.value = 0; resetLoading.value = false
  captchaQuestion.value = ''; captchaAnswer.value = ''; captchaError.value = ''
  captchaAttempts.value = 0; captchaLoading.value = false
  loginLoading.value = false
  showLoginPw.value = false
  showRegPw.value = false
  showResetPw.value = false
}

// Login
const loginUser = ref(''); const loginPass = ref('')
const loginError = ref(''); const loginLoading = ref(false)

async function handleLogin() {
  const u = loginUser.value.trim()
  const p = loginPass.value
  if (!u || !p) { loginError.value = '请输入用户名和密码'; return }
  loginError.value = ''; loginLoading.value = true
  try {
    const data = await apiLogin(u, p)
    if (data && data.ok) {
      // Password correct → show captcha
      loginLoading.value = false
      loginPass.value = ''
      captchaMode.value = 'login'
      captchaToken.value = data.username
      sessionToken.value = data.token || ''
      flow.value = 'login-captcha'
      await loadCaptcha()
    } else {
      const msg = data && data.error ? data.error : '服务器返回异常'
      loginError.value = msg + (data ? ` (code: ${JSON.stringify(data)})` : '')
      loginLoading.value = false
    }
  } catch (e) {
    const status = e.status || '网络'
    const hint = status === 404 ? '未检索到该账号，请注册' :
                 status === 401 ? '密码错误' :
                 `HTTP ${status}`
    loginError.value = `${hint}（${status}）`
    loginLoading.value = false
  }
}


async function testConnection() {
  loginError.value = '检测中...'
  loginLoading.value = true
  try {
    const r = await fetch('/health', { method: 'GET' })
    if (r.ok) {
      const data = await r.json()
      loginError.value = `✅ 后端连接正常 (db: ${data.db})`
    } else {
      loginError.value = `❌ 后端响应异常 (HTTP ${r.status})`
    }
  } catch (e) {
    loginError.value = `❌ 无法连接后端: ${e.message}`
  }
  loginLoading.value = false
}

// Register
const regUser = ref(''); const regPass = ref(''); const regError = ref('')
const secQuestion = ref(''); const secAnswer = ref(''); const secError = ref('')

function goRegister1() { resetAll(); flow.value = 'register-1' }
async function goRegister2() {
  const u = regUser.value.trim()
  const p = regPass.value
  if (!u) { regError.value = '请输入用户名'; return }
  if (u.length > 8) { regError.value = '用户名不超过8个字符'; return }
  if (!/^[a-zA-Z0-9]+$/.test(u)) { regError.value = '用户名只能使用字母和数字'; return }
  if (p.length < 8) { regError.value = '密码不少于8个字符'; return }
  regError.value = ''
  // Quick username availability check
  try {
    const data = await checkUsername(u)
    if (data.exists) { regError.value = '该用户名已存在'; return }
  } catch { /* proceed anyway, backend will validate */ }
  flow.value = 'register-2'
}
function goRegister3() {
  if (!secQuestion.value) { secError.value = '请选择密保问题'; return }
  if (!secAnswer.value.trim()) { secError.value = '密保答案不能为空'; return }
  secError.value = ''; flow.value = 'register-3'
  loadCaptcha()
}

// Captcha
const captchaMode = ref('login')
const captchaToken = ref('')
const sessionToken = ref('')
const captchaQuestion = ref(''); const captchaAnswer = ref('')
const captchaError = ref(''); const captchaLoading = ref(false)
const captchaAttempts = ref(0)

function cancelCaptcha() {
  resetAll()
  flow.value = 'login'
}
async function loadCaptcha() {
  try {
    const data = await apiCaptcha()
    captchaQuestion.value = data.question
    captchaAnswer.value = ''; captchaError.value = ''
    await nextTick()
    document.querySelector('input[type="number"]')?.focus()
  } catch (e) { captchaError.value = '获取验证码失败 (' + (e.message || e.status || '网络') + ')' }
}

async function handleCaptcha() {
  const isLogin = flow.value === 'login-captcha'
  if (captchaAttempts.value >= 3) {
    if (isLogin) { loginError.value = '验证失败次数过多'; flow.value = 'login'; return }
    flow.value = 'register-1'; regError.value = '验证失败次数过多'; return
  }
  const answer = parseInt(captchaAnswer.value)
  if (isNaN(answer)) { captchaError.value = '请输入正确答案'; return }
  const parts = captchaQuestion.value.replace(' = ?', '').split(' ')
  if (parts.length !== 3) { captchaError.value = '验证码异常'; return }
  const a = parseInt(parts[0]), op = parts[1], b = parseInt(parts[2])
  let correct
  if (op === '+') correct = a + b
  else if (op === '-') correct = a - b
  else if (op === '×') correct = a * b
  if (answer !== correct) {
    captchaAttempts.value++
    if (captchaAttempts.value >= 3) {
      if (isLogin) { loginError.value = '验证失败次数过多'; flow.value = 'login'; return }
      flow.value = 'register-1'; regError.value = '验证失败次数过多'; return
    }
    captchaError.value = `答案错误，剩余 ${3 - captchaAttempts.value} 次`
    await loadCaptcha(); return
  }
  // Captcha correct — proceed
  captchaLoading.value = true
  if (isLogin) {
    setAuthed(captchaToken.value, sessionToken.value)
    emit('authed')
  } else {
    try {
      const data = await apiRegister(regUser.value.trim(), regPass.value, secQuestion.value, secAnswer.value.trim())
      if (data.ok) {
        loginUser.value = data.username; loginPass.value = ''
        resetAll(); flow.value = 'login'; loginError.value = '✅ 注册成功，请登录'
      } else {
        regError.value = data.error || '注册失败'
        flow.value = 'register-1'
      }
    } catch (e) {
      regError.value = e.status === 403 ? '注册名额已满' : '注册失败'
      flow.value = 'register-1'
    }
  }
  captchaLoading.value = false
}

// Password Reset
const resetUser = ref(''); const resetAnswer = ref(''); const resetNewPass = ref('')
const resetQuestion = ref(''); const resetError = ref('')
const resetAttempts = ref(0); const resetLoading = ref(false)

function goReset1() { resetAll(); flow.value = 'reset-1' }

async function checkResetUser() {
  const u = resetUser.value.trim()
  if (!u) { resetError.value = '请输入用户名'; return }
  resetError.value = ''
  try {
    const data = await apiGetSecurity(u)
    if (data.error) { resetError.value = data.error; return }
    resetQuestion.value = data.question
    resetAttempts.value = 0
    flow.value = 'reset-2'
  } catch (e) {
    resetError.value = e.status === 404 ? '该账号不存在' : '查询失败'
  }
}

async function checkSecurityAnswer() {
  if (!resetAnswer.value.trim()) { resetError.value = '请输入答案'; return }
  resetError.value = ''
  try {
    const data = await apiVerifySecurity(resetUser.value.trim(), resetAnswer.value.trim())
    if (data.ok) {
      flow.value = 'reset-3'
    } else {
      resetAttempts.value++
      if (resetAttempts.value >= 3) {
        resetError.value = '验证失败次数过多'
        setTimeout(() => { flow.value = 'login'; resetAll() }, 1500)
        return
      }
      resetError.value = `答案错误，剩余 ${3 - resetAttempts.value} 次`
    }
  } catch { resetError.value = '验证失败' }
}

async function handleResetPassword() {
  const p = resetNewPass.value
  if (p.length < 8) { resetError.value = '密码不少于8个字符'; return }
  resetError.value = ''; resetLoading.value = true
  try {
    const data = await apiResetPassword(resetUser.value.trim(), p)
    if (data.ok) {
      resetError.value = ''
      resetAll()
      flow.value = 'login'
      loginError.value = '✅ 密码修改成功，请重新登录'
    }
  } catch { resetError.value = '修改失败' }
  finally { resetLoading.value = false }
}
</script>
