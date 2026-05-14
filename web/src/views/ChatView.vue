<template>
  <!-- Mobile sidebar overlay -->
  <Teleport to="body" v-if="showMobileMenu">
    <div class="fixed inset-0 z-40 md:hidden" @click="showMobileMenu = false">
      <div class="absolute inset-0 bg-black/50" />
      <aside class="absolute left-0 top-0 bottom-0 w-60 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div class="h-14 flex items-center gap-2 px-4 border-b border-slate-800">
          <span class="text-xl">🦆</span>
          <span class="font-semibold text-duck-400">Duck</span>
          <span class="text-slate-300 font-semibold">Chat</span>
        </div>
        <nav class="flex-1 p-2 space-y-1" @click="showMobileMenu = false">
          <router-link to="/" class="sidebar-link" :class="{ active: $route.name === 'chat' }">💬 对话</router-link>
          <router-link to="/history" class="sidebar-link" :class="{ active: $route.name === 'history' }">🕐 历史</router-link>
          <router-link to="/settings" class="sidebar-link" :class="{ active: $route.name === 'settings' }">⚙️ 设置</router-link>
        </nav>
      </aside>
    </div>
  </Teleport>

  <!-- Header -->
  <ChatHeader
    :providers="providers"
    :current-model="currentModel"
    :loading="loading"
    :cloud-authed="isAuthed"
    @toggle-cloud="showAuthModal = true"
    @model-change="onModelChange"
    @toggle-mobile-menu="showMobileMenu = !showMobileMenu"
  />

  <!-- Messages -->
  <div ref="chatContainer" class="flex-1 overflow-y-auto px-4 py-4 space-y-4">
    <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full text-slate-500">
      <span class="text-6xl mb-4">🦆</span>
      <p class="text-lg font-medium text-slate-400 mb-1">选择模型开始对话</p>
      <p class="text-sm">左侧切换模型，输入消息按回车发送</p>
    </div>

    <MessageBubble
      v-for="msg in messages"
      :key="msg.id"
      :msg="msg"
      :streaming="streaming && msg === messages[messages.length - 1] && msg.role === 'assistant'"
    />
  </div>

  <!-- Input -->
  <form class="flex gap-2 px-4 py-3 bg-slate-900/60 border-t border-slate-800 shrink-0" @submit.prevent="send">
    <input
      v-model="inputText"
      class="input-field"
      :placeholder="currentModel ? '输入消息，回车发送…' : '请先选择模型'"
      :disabled="!currentModel || streaming"
      autofocus
    />
    <button
      type="submit"
      class="btn-primary flex items-center gap-1.5"
      :disabled="!inputText.trim() || !currentModel || streaming"
    >
      <span>发送</span>
      <svg v-if="!streaming" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19V5m0 0l-7 7m7-7l7 7"/></svg>
      <span v-else class="w-4 h-4 block rounded-full border-2 border-t-transparent border-current animate-spin"></span>
    </button>
  </form>

  <!-- Auth modal -->
  <AuthGate v-if="showAuthModal" @close="showAuthModal = false" @auth="handleAuth" />
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useAuth } from '@/composables/useAuth'
import { useModels } from '@/composables/useModels'
import { useChat } from '@/composables/useChat'
import { sendChatMessage } from '@/api'
import ChatHeader from '@/components/ChatHeader.vue'
import MessageBubble from '@/components/MessageBubble.vue'
import AuthGate from '@/components/AuthGate.vue'

const { isAuthed, cloudKey, login } = useAuth()
const { providers, currentModel, loading, load } = useModels()
const { messages, streaming, addMessage, clearMessages, startStream } = useChat()

const inputText = ref('')
const chatContainer = ref(null)
const showAuthModal = ref(false)
const showMobileMenu = ref(false)

onMounted(() => {
  load(!!cloudKey.value)
})

function onModelChange(val) {
  currentModel.value = val
}

async function send() {
  const msg = inputText.value.trim()
  if (!msg || !currentModel.value || streaming.value) return
  inputText.value = ''

  addMessage(msg, 'user')
  const bubble = addMessage('', 'assistant')
  await nextTick()
  scrollToBottom()

  try {
    const body = await sendChatMessage(currentModel.value, msg, cloudKey.value)
    await startStream(body, bubble)
  } catch (e) {
    if (e.status === 401) {
      bubble.text = '[需要云端密钥]'
      bubble.role = 'error'
    } else {
      bubble.text = `[HTTP ${e.status}]`
      bubble.role = 'error'
    }
  }
  scrollToBottom()
}

async function handleAuth(key) {
  const result = await login(key)
  if (result.ok) {
    showAuthModal.value = false
    await load(true)
  }
  // If login fails, the AuthGate sees the emit but we don't close
  // The parent should ideally show the error from the child
  if (!result.ok) {
    // If user already closed it, ignore
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

watch(messages, scrollToBottom, { deep: true })
</script>
