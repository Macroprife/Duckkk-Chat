<template>
  <div
    class="fade-in"
    :class="{
      'msg-bubble-user': msg.role === 'user',
      'msg-bubble-assistant': msg.role === 'assistant',
      'msg-bubble-error': msg.role === 'error',
    }"
  >
    <!-- Streaming indicator -->
    <div v-if="streaming && text === ''" class="typing-cursor text-slate-400"></div>

    <!-- Rendered markdown for assistant messages -->
    <div v-else-if="msg.role === 'assistant'" class="markdown-body" v-html="rendered"></div>

    <!-- Plain text for user / error -->
    <div v-else class="whitespace-pre-wrap break-words leading-relaxed text-sm">{{ text }}</div>

    <!-- Copy button on assistant messages -->
    <button
      v-if="msg.role === 'assistant' && text && !streaming"
      class="mt-2 text-xs text-slate-500 hover:text-slate-300 transition-colors"
      @click="copy"
    >
      {{ copied ? '✅ 已复制' : '📋 复制' }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { renderMarkdown } from '@/composables/useChat'

const props = defineProps({
  msg: { type: Object, required: true },
  streaming: { type: Boolean, default: false },
})

const text = computed(() => props.msg.text || '')
const rendered = computed(() => renderMarkdown(text.value))

const copied = ref(false)
async function copy() {
  try {
    await navigator.clipboard.writeText(text.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {}
}
</script>
