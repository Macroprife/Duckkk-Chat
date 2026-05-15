<template>
  <div class="flex flex-col h-full bg-[#f7f5f2]">
    <!-- Header -->
    <div class="h-14 flex items-center gap-2 px-4 border-b border-[#e8e4df] shrink-0 bg-white">
      <button class="btn-ghost p-1 text-lg leading-none" @click="$router.push('/')">←</button>
      <h2 class="text-sm font-semibold text-gray-700">🕐 对话历史</h2>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-4">
      <div v-if="loading" class="text-center text-gray-400 py-12">加载中...</div>

      <div v-else-if="conversations.length === 0" class="text-center text-gray-400 py-12">
        <p class="text-4xl mb-3">📭</p>
        <p>还没有对话记录</p>
      </div>

      <div v-else class="max-w-2xl mx-auto space-y-2">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="flex items-center gap-3 p-4 rounded-xl bg-white border border-[#e8e4df] hover:border-[#d6d0c8] cursor-pointer transition-all shadow-sm"
          @click="openModal(conv)"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm text-gray-700 truncate">{{ conv.title || '新对话' }}</p>
            <p class="text-xs text-gray-400 mt-0.5">
              {{ formatTime(conv.created_at) }} · {{ conv.model_id }}
            </p>
          </div>
          <span class="text-xs text-gray-400">{{ conv.provider }}</span>
        </div>
      </div>
    </div>

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

function openModal(conv) { selectedConv.value = conv }
function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>
