<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="h-14 flex items-center px-4 border-b border-slate-800 shrink-0 bg-slate-900/40">
      <h2 class="text-sm font-semibold text-slate-200 flex items-center gap-2">
        🕐 对话历史
      </h2>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-4">
      <div v-if="loading" class="text-center text-slate-500 py-12">加载中...</div>

      <div v-else-if="conversations.length === 0" class="text-center text-slate-500 py-12">
        <p class="text-4xl mb-3">📭</p>
        <p>还没有对话记录</p>
      </div>

      <div v-else class="max-w-2xl mx-auto space-y-2">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="flex items-center gap-3 p-3 rounded-xl bg-slate-900/40 border border-slate-800/60 hover:border-slate-700 cursor-pointer transition-all"
          @click="openModal(conv)"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm text-slate-200 truncate">{{ conv.title || '新对话' }}</p>
            <p class="text-xs text-slate-500 mt-0.5">
              {{ formatTime(conv.created_at) }} · {{ conv.model_id }}
            </p>
          </div>
          <span class="text-xs text-slate-500">{{ conv.provider }}</span>
        </div>
      </div>
    </div>

    <!-- Conversation modal -->
    <ConversationModal
      v-if="selectedConv"
      :conversation-id="selectedConv.id"
      :title="selectedConv.title"
      :model="selectedConv.model_id"
      :created-at="selectedConv.created_at"
      @close="selectedConv = null"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchConversations } from '@/api'
import ConversationModal from '@/components/ConversationModal.vue'

const conversations = ref([])
const loading = ref(true)
const selectedConv = ref(null)

onMounted(async () => {
  try {
    const data = await fetchConversations()
    conversations.value = data.conversations || []
  } catch (e) {
    console.error('Failed to load conversations', e)
  } finally {
    loading.value = false
  }
})

function openModal(conv) {
  selectedConv.value = conv
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>
