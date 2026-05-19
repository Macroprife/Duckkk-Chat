<template>
  <div class="flex gap-3 items-start fade-in" :class="msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'">
    <!-- Avatar -->
    <div
      class="w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 mt-0.5 shadow-sm"
      :class="msg.role === 'user' ? 'bg-duck-100 text-duck-600' : 'bg-gray-200 text-gray-500'"
    >
      <img v-if="msg.role === 'assistant'" src="/duck-icon.svg" alt="AI" class="w-5 h-5" />
      <span v-else>👤</span>
    </div>

    <!-- Bubble -->
    <div
      :class="{
        'msg-bubble-user': msg.role === 'user',
        'msg-bubble-assistant': msg.role === 'assistant',
        'msg-bubble-error': msg.role === 'error',
      }"
    >
      <!-- Streaming indicator -->
      <div v-if="streaming && text === ''" class="typing-cursor min-w-[1ch]"></div>

      <!-- Rendered markdown for assistant messages -->
      <div v-else-if="msg.role === 'assistant'" class="markdown-body text-sm leading-relaxed" v-html="rendered"></div>

      <!-- Image + plain text for user / error messages -->
      <template v-else>
        <div v-if="msg.image" class="mb-2">
          <img :src="msg.image" class="max-w-full max-h-64 rounded-lg object-contain border border-gray-200" />
        </div>
        <div v-if="text" class="whitespace-pre-wrap break-words leading-relaxed text-sm">{{ text }}</div>
      </template>

      <!-- Copy button on assistant messages -->
      <button
        v-if="msg.role === 'assistant' && text && !streaming"
        class="mt-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
        @click="copy"
      >
        {{ copied ? '✅ 已复制' : '📋 复制' }}
      </button>
    </div>
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
