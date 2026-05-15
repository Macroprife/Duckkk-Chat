<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" @click.self="$emit('close')">
      <div class="bg-white border border-[#e8e4df] rounded-2xl w-full max-w-3xl max-h-[85vh] mx-4 flex flex-col shadow-xl fade-in">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-[#e8e4df] shrink-0">
          <div>
            <h3 class="text-sm font-semibold text-gray-700">{{ title || '对话详情' }}</h3>
            <p class="text-xs text-gray-400 mt-0.5">{{ model }} · {{ formatTime(createdAt) }}</p>
          </div>
          <button class="btn-ghost text-lg leading-none p-1" @click="$emit('close')">✕</button>
        </div>

        <div ref="scrollRef" class="flex-1 overflow-y-auto px-6 py-4 space-y-4 bg-[#f7f5f2]">
          <div v-if="loading" class="text-center text-gray-400 py-12">加载中...</div>
          <template v-else>
            <div v-for="msg in messages" :key="msg.id" class="fade-in"
              :class="msg.role === 'user'
                ? 'max-w-[80%] ml-auto rounded-2xl rounded-br-md px-4 py-3 bg-duck-500 text-white'
                : msg.role === 'error'
                  ? 'max-w-[80%] mx-auto rounded-2xl px-4 py-3 bg-red-50 text-red-600 border border-red-200 text-center'
                  : 'max-w-[80%] rounded-2xl rounded-bl-md px-4 py-3 bg-white border border-[#e8e4df] text-gray-800 shadow-sm'">
              <div v-if="msg.role === 'assistant'" class="markdown-body text-sm leading-relaxed" v-html="renderMd(msg.content)"></div>
              <div v-else class="whitespace-pre-wrap break-words text-sm leading-relaxed">{{ msg.content }}</div>
              <p class="text-xs text-gray-400 mt-1.5">{{ msg.role === 'user' ? '你' : 'AI' }}</p>
            </div>
          </template>
        </div>

        <div class="px-6 py-3 border-t border-[#e8e4df] shrink-0 flex justify-end bg-white">
          <button class="btn-ghost text-gray-500" @click="$emit('close')">关闭</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { fetchConversation } from '@/api'
import { renderMarkdown } from '@/composables/useChat'

const props = defineProps({
  conversationId: { type: String, required: true },
  title: String,
  model: String,
  createdAt: String,
})
defineEmits(['close'])

const messages = ref([])
const loading = ref(true)
const scrollRef = ref(null)
function renderMd(text) { return renderMarkdown(text || '') }
function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  try {
    const data = await fetchConversation(props.conversationId)
    messages.value = data.messages || []
  } catch (e) { console.error('load error', e) }
  finally {
    loading.value = false
    await nextTick()
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  }
})
</script>
