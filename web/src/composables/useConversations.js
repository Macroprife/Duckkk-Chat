import { ref } from 'vue'
import {
  fetchConversations,
  apiCreateConversation as apiCreate,
  apiUpdateConversation as apiRename,
  apiDeleteConversation as apiDelete,
} from '@/api'

// Module-level shared state
const conversations = ref([])
const activeConversationId = ref(sessionStorage.getItem('duck_active_conv') || '')
const loading = ref(false)

export function useConversations() {
  async function loadConversations() {
    loading.value = true
    try {
      const data = await fetchConversations(50)
      conversations.value = data.conversations || []
    } catch (e) {
      console.error('load conversations error', e)
    } finally {
      loading.value = false
    }
  }

  async function createConversation(modelId) {
    const data = await apiCreate(modelId)
    if (!data.ok) throw new Error(data.error || 'create failed')
    const conv = data.conversation
    conversations.value.unshift(conv)
    setActive(conv.id)
    return conv
  }

  async function renameConversation(id, title) {
    await apiRename(id, title)
    const conv = conversations.value.find(c => c.id === id)
    if (conv) conv.title = title
  }

  async function deleteConversation(id) {
    await apiDelete(id)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (activeConversationId.value === id) {
      if (conversations.value.length > 0) {
        setActive(conversations.value[0].id)
      } else {
        setActive('')
      }
    }
  }

  function setActive(id) {
    activeConversationId.value = id
    if (id) {
      sessionStorage.setItem('duck_active_conv', id)
    } else {
      sessionStorage.removeItem('duck_active_conv')
    }
  }

  return {
    conversations,
    activeConversationId,
    loading,
    loadConversations,
    createConversation,
    renameConversation,
    deleteConversation,
    setActive,
  }
}
