<template>
  <!-- Rotation warning toast -->
  <Teleport to="body">
    <div
      v-if="rotationWarning && rotationWarning.remaining <= 30"
      class="fixed top-4 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-xl bg-amber-50 border border-amber-200 shadow-lg text-sm text-amber-800 flex items-center gap-2 fade-in"
    >
      <span>⏰</span>
      <span>云端模型将于 <strong>{{ rotationWarning.remaining }}</strong> 秒后自动关闭</span>
    </div>
  </Teleport>

  <!-- Mobile sidebar overlay -->
  <Teleport to="body" v-if="showMobileMenu">
    <div class="fixed inset-0 z-40 md:hidden" @click="showMobileMenu = false">
      <div class="absolute inset-0 bg-black/40" />
      <Sidebar mobile @close="showMobileMenu = false" @new-chat="onNewChat" @switch-conv="onSwitchConv" />
    </div>
  </Teleport>

  <!-- ============ SEARCH MODE ============ -->
  <template v-if="mode === 'search'">
    <ChatHeader
      :providers="providers"
      :current-model="currentModel"
      :loading="loading"
      :cloud-authed="isAuthed"
      @toggle-cloud="handleCloudClick"
      @model-change="onModelChange"
      @toggle-mobile-menu="showMobileMenu = !showMobileMenu"
    />

    <div class="flex-1 flex items-center justify-center bg-gray-50 px-6">
      <div class="w-full max-w-xl text-center">

        <!-- Brand -->
        <div class="mb-4">
          <img src="/duck-icon.svg" alt="Duck Chat" class="w-16 h-16 mx-auto" />
        </div>
        <h1 class="text-2xl font-semibold text-gray-800 mb-1">Duck Chat</h1>
        <p class="text-sm text-gray-400 mb-8">你的本地 AI 助手 · 基于 Ollama + OpenClaw</p>
        <p class="text-xs text-amber-500 mb-6">温馨提示：建议在模型回答生成完毕后再进行对话切换，存在双行输出</p>

        <!-- Pill search input -->
        <div class="relative">
          <div class="flex items-center gap-2 bg-white border border-gray-200 rounded-full px-4 py-2 shadow-lg focus-within:border-duck-400 focus-within:ring-2 focus-within:ring-duck-200 transition-all duration-200">
            <!-- Image upload (gemma3:4b / cloud only) -->
            <button
              v-if="canUploadImage"
              class="w-9 h-9 rounded-full flex items-center justify-center transition-all shrink-0"
              :class="selectedImage ? 'bg-duck-100 text-duck-600' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'"
              @click="pickImage"
              :title="selectedImage ? '已选择图片' : '上传图片'"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
              </svg>
            </button>

            <div v-if="selectedImage" class="shrink-0">
              <img :src="selectedImage" class="w-8 h-8 rounded object-cover border border-gray-200" />
            </div>
            <input
              ref="searchInput"
              v-model="inputText"
              class="flex-1 bg-transparent border-none outline-none text-sm text-gray-800 placeholder-gray-400 py-2"
              placeholder="输入消息，回车发送…"
              :disabled="!currentModel"
              @keydown.enter.prevent="send"
            />

            <!-- Send button inside pill -->
            <button
              type="button"
              class="w-9 h-9 rounded-full flex items-center justify-center transition-all duration-150 shrink-0"
              :class="inputText.trim()
                ? 'bg-duck-500 text-white hover:bg-duck-600 shadow-sm'
                : 'bg-gray-100 text-gray-300'"
              :disabled="!inputText.trim() || !currentModel"
              @click="send"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 12h14m-7-7l7 7-7 7"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Suggested prompts -->
        <div class="mt-6 flex flex-wrap gap-2 justify-center">
          <button
            v-for="s in suggestions"
            :key="s.text"
            class="px-4 py-2 rounded-full text-xs border border-gray-200 text-gray-500 bg-white hover:border-duck-300 hover:text-duck-600 hover:bg-duck-50 transition-all shadow-sm"
            @click="useSuggestion(s)"
          >
            {{ s.label }}
          </button>
        </div>
      </div>
    </div>
  </template>

  <!-- ============ CHAT MODE ============ -->
  <template v-else>
    <!-- Chat header with close button -->
    <div class="h-14 flex items-center gap-3 px-4 border-b border-gray-200 shrink-0 bg-white">
      <button class="md:hidden btn-ghost text-lg p-1" @click="showMobileMenu = !showMobileMenu">☰</button>

      <!-- Model selector (compact) -->
      <div class="flex items-center gap-2">
        <select
          class="bg-transparent text-gray-600 text-sm outline-none cursor-pointer"
          :value="currentModel"
          :disabled="loading"
          @change="onModelChange($event.target.value)"
        >
          <option value="" disabled v-if="loading">加载中...</option>
          <optgroup v-for="g in providers" :key="g.provider" :label="g.provider">
            <option v-for="m in g.models" :key="m.id" :value="m.id">
              {{ m.name }}{{ m.size ? ` (${m.size})` : '' }}
            </option>
          </optgroup>
        </select>
      </div>

      <!-- Right side -->
      <div class="ml-auto flex items-center gap-2">
        <!-- Cloud toggle -->
        <button
          class="btn-ghost flex items-center gap-1.5 text-xs"
          :class="isAuthed ? 'text-emerald-600' : ''"
          @click="handleCloudClick"
        >
          <span>{{ isAuthed ? '✅' : '🔒' }}</span>
          <span class="hidden sm:inline text-xs">{{ isAuthed ? '已连接' : '云端' }}</span>
        </button>

        <!-- Close / back to search -->
        <button
          class="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all"
          @click="mode = 'search'"
          title="回到首页"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Messages area -->
    <div ref="chatContainer" class="flex-1 overflow-y-auto px-4 py-6 bg-gray-50">
      <div class="max-w-3xl mx-auto space-y-5">
        <div v-if="messages.length === 0" class="flex flex-col items-center justify-center min-h-[300px] text-gray-400">
          <p class="text-sm text-gray-400">新对话，发送第一条消息</p>
        </div>

        <MessageBubble
          v-for="msg in messages"
          :key="msg.id"
          :msg="msg"
          :streaming="streaming && msg === messages[messages.length - 1] && msg.role === 'assistant'"
        />
      </div>
    </div>

    <!-- Chat input -->
    <div class="border-t border-gray-200 bg-white shadow-2xl relative z-10">
      <div class="max-w-3xl mx-auto px-4 py-3">
        <!-- Image preview -->
        <div v-if="selectedImage" class="mb-2 flex items-center gap-2">
          <img :src="selectedImage" class="w-12 h-12 rounded-lg object-cover border border-gray-200" />
          <button class="text-xs text-red-500 hover:text-red-600" @click="clearImage">移除图片</button>
        </div>
        <div class="flex gap-2 items-start">
          <!-- Image upload button -->
          <button
            v-if="canUploadImage"
            class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-1 transition-all"
            :class="selectedImage ? 'bg-duck-100 text-duck-600' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'"
            @click="pickImage"
            :title="selectedImage ? '已选择图片' : '上传图片'"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
            </svg>
          </button>
          <div class="relative flex-1">
            <input
              v-model="inputText"
              class="w-full rounded-xl border border-gray-200 bg-gray-50 px-5 py-3.5 pr-12 text-sm text-gray-800
                     placeholder-gray-400 outline-none focus:border-duck-400 focus:ring-2 focus:ring-duck-200
                     transition-all duration-150 shadow-inner"
              :placeholder="currentModel ? '回复 Duck Chat...' : '请先选择模型'"
              :disabled="!currentModel || streaming"
              autofocus
              @keydown.enter.prevent="send"
            />
            <button
              v-if="!streaming"
              type="button"
              class="absolute right-1.5 top-1/2 -translate-y-1/2 w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-150"
              :class="inputText.trim()
                ? 'bg-duck-500 text-white hover:bg-duck-600 shadow-sm'
                : 'text-gray-300 cursor-default'"
              :disabled="!inputText.trim() || !currentModel"
              @click="send"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 12h14m-7-7l7 7-7 7"/>
              </svg>
            </button>
            <button
              v-else
              type="button"
              class="absolute right-1.5 top-1/2 -translate-y-1/2 w-9 h-9 flex items-center justify-center rounded-lg bg-red-500 text-white hover:bg-red-600 shadow-sm transition-all duration-150"
              @click="stopStream"
              title="停止生成"
            >
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </template>

  <AuthGate v-if="showAuthModal" @close="showAuthModal = false" @auth="handleAuth" />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useCloudKey } from '@/composables/useCloudKey'
import { useModels } from '@/composables/useModels'
import { useChat } from '@/composables/useChat'
import { useConversations } from '@/composables/useConversations'
import { sendChatMessage, fetchConversation } from '@/api'
import ChatHeader from '@/components/ChatHeader.vue'
import MessageBubble from '@/components/MessageBubble.vue'
import AuthGate from '@/components/AuthGate.vue'
import Sidebar from '@/components/Sidebar.vue'

const { isAuthed, cloudKey, login, logout } = useCloudKey()
const { providers, currentModel, loading, load } = useModels()
const { messages, streaming, addMessage, clearMessages, startStream, stopStream, createAbortSignal } = useChat()
const {
  conversations,
  activeConversationId,
  loadConversations,
  createConversation,
  setActive,
} = useConversations()

const mode = ref('search')
const inputText = ref('')
const chatContainer = ref(null)
const showAuthModal = ref(false)
const showMobileMenu = ref(false)
const searchInput = ref(null)
const selectedImage = ref(null)
const rotationWarning = ref(null)  // null | { remaining: number }
let _rotationPoller = null
let _lastRotationVersion = -1
const imageInputRef = ref(null)

const canUploadImage = computed(() => {
  const m = currentModel.value
  // 云端模型不支持识图，只有本地 gemma3:4b 可以
  return m === 'ollama/gemma3:4b'
})

function pickImage() {
  const el = document.createElement('input')
  el.type = 'file'
  el.accept = 'image/*'
  el.onchange = () => {
    const file = el.files[0]
    if (!file) return
    // Compress to max 1200px wide and ~80% quality to keep payload reasonable
    const img = new Image()
    img.onload = () => {
      let w = img.width, h = img.height
      const maxDim = 1200
      if (w > maxDim || h > maxDim) {
        if (w > h) { h = h * maxDim / w; w = maxDim }
        else { w = w * maxDim / h; h = maxDim }
      }
      const canvas = document.createElement('canvas')
      canvas.width = w; canvas.height = h
      canvas.getContext('2d').drawImage(img, 0, 0, w, h)
      selectedImage.value = canvas.toDataURL('image/jpeg', 0.8)
    }
    const reader = new FileReader()
    reader.onload = (e) => { img.src = e.target.result }
    reader.readAsDataURL(file)
  }
  el.click()
}

function clearImage() { selectedImage.value = null }



const suggestions = [
  { label: '✍️ 写文案', text: '帮我写一段产品推广文案' },
  { label: '💻 写代码', text: '用 Python 写一个网页爬虫' },
  { label: '🌐 翻译', text: '把这段话翻译成英文：' },
  { label: '📝 总结', text: '帮我总结一下这段内容：' },
]

onMounted(() => {
  load(!!cloudKey.value)
  loadConversations().then(() => {
    if (activeConversationId.value) {
      loadActiveConversation()
      if (messages.value.length > 0) mode.value = 'chat'
    }
  })
  startRotationPoller()
})

let _sendInProgress = false

watch(activeConversationId, (newId, oldId) => {
  if (_sendInProgress) return
  if (newId && newId !== oldId) {
    loadActiveConversation()
  } else if (!newId && oldId) {
    // Active conversation cleared (e.g. deleted, rotated) → clear messages too
    clearMessages()
  }
})

watch(currentModel, (val) => {
  if (val) sessionStorage.setItem('duck_last_model', val)
})

async function loadActiveConversation() {
  const id = activeConversationId.value
  if (!id) { clearMessages(); return }
  try {
    const data = await fetchConversation(id)
    clearMessages()
    for (const m of (data.messages || [])) addMessage(m.content || '', m.role)
    await nextTick(); scrollToBottom()
  } catch (e) { console.error('load error', e); clearMessages() }
}

function onModelChange(val) { currentModel.value = val }
function onNewChat() {
  clearMessages()
  clearImage()
  mode.value = 'search'
  nextTick(() => scrollToBottom())
}
function onSwitchConv() { mode.value = 'chat'; loadActiveConversation() }

function useSuggestion(s) {
  inputText.value = s.text
  searchInput.value?.focus()
}

async function send() {
  console.log('[duck] send triggered, mode:', mode.value)
  const msg = inputText.value.trim()
  if (!msg || !currentModel.value || streaming.value) return
  inputText.value = ''

  // Guard: set flag BEFORE createConversation to prevent watch from firing loadActiveConversation
  _sendInProgress = true

  let convId = activeConversationId.value
  if (!convId) {
    try {
      const conv = await createConversation(currentModel.value)
      convId = conv.id
    } catch (e) {
      console.error('[duck] create failed:', e)
      _sendInProgress = false
      addMessage(`创建对话失败: ${e.message}`, 'error')
      return
    }
  }

  mode.value = 'chat'

  addMessage(msg, 'user', selectedImage.value)
  const bubble = addMessage('', 'assistant')
  await nextTick(); scrollToBottom()

  try {
    console.log('[duck] sending...', selectedImage.value ? 'with image' : 'text only')
    const signal = createAbortSignal()
    const resp = await sendChatMessage(currentModel.value, msg, convId, cloudKey.value, selectedImage.value, signal)
    clearImage()
    const rid = resp.headers.get('X-Conversation-Id')
    if (rid && rid !== activeConversationId.value) setActive(rid)
    await startStream(resp.body, bubble)
  } catch (e) {
    console.error('[duck] send error:', e)
    if (e.status === 401) {
      bubble.text = '[云端密钥已过期，请重新连接]'
      bubble.role = 'error'
      // 自动清除旧的密钥缓存
      logout()
      load(false)
      setTimeout(() => { showAuthModal.value = true }, 1500)
    }
    else if (e.status === 404) {
      bubble.text = '[对话已不存在]'; bubble.role = 'error'
      conversations.value = conversations.value.filter(c => c.id !== activeConversationId.value)
      setActive(conversations.value.length > 0 ? conversations.value[0].id : '')
    } else { bubble.text = `[HTTP ${e.status}]`; bubble.role = 'error' }
  } finally {
    _sendInProgress = false
    await loadConversations()
  }
  scrollToBottom()
}

function handleCloudClick() {
  if (isAuthed.value) {
    if (confirm('确定断开云端连接？断开后云端模型将被隐藏。')) {
      logout()
      load(false)
    }
  } else {
    showAuthModal.value = true
  }
}

async function handleAuth(key) {
  const r = await login(key)
  if (r.ok) { showAuthModal.value = false; await load(true) }
}

function startRotationPoller() {
  _rotationPoller = setInterval(async () => {
    if (!isAuthed.value) {
      rotationWarning.value = null
      return
    }
    try {
      const r = await fetch('/api/cloud/rotation-status')
      const data = await r.json()
      if (!data.ok) return

      const secs = data.seconds_remaining
      const ver = data.rotation_version

      // First poll — remember version
      if (_lastRotationVersion === -1) {
        _lastRotationVersion = ver
      }

      // Show warning at 30s
      if (secs <= 30 && secs > 0) {
        rotationWarning.value = { remaining: secs }
      }

      // Version changed → key was rotated
      if (ver !== _lastRotationVersion && !_sendInProgress) {
        _lastRotationVersion = ver
        rotationWarning.value = null
        logout()
        try { await load(false) } catch {}
        setActive('')
        mode.value = 'search'
      }
    } catch {}
  }, 5000)
}

onUnmounted(() => {
  if (_rotationPoller) clearInterval(_rotationPoller)
})

function scrollToBottom() {
  nextTick(() => { if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight })
}
watch(messages, scrollToBottom, { deep: true })
</script>
