<template>
  <component :is="mobile ? 'div' : 'aside'"
    :class="mobile
      ? 'absolute left-0 top-0 bottom-0 w-60 bg-[#f5f0eb] border-r border-[#e8e0d6] flex flex-col z-10'
      : 'w-60 bg-[#f5f0eb] border-r border-[#e8e0d6] flex flex-col shrink-0 hidden md:flex'"
  >
    <!-- Branding -->
    <div class="h-14 flex items-center gap-2.5 px-4 border-b border-[#e8e0d6] shrink-0">
      <img src="/duck-icon.svg" alt="Duck" class="w-7 h-7" />
      <span class="font-semibold text-duck-600">Duck</span>
      <span class="text-gray-600 font-semibold">Chat</span>
    </div>

    <!-- New chat button -->
    <div class="px-2 pt-2 shrink-0">
      <button
        class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-gray-600
               bg-white border border-[#e8e0d6] hover:bg-[#ebe6e0]
               hover:border-[#ddd5cb] transition-all duration-150 shadow-sm"
        @click="handleNewChat"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        <span>新对话</span>
      </button>
    </div>

    <!-- Conversation list -->
    <div class="flex-1 overflow-y-auto p-2 space-y-0.5 min-h-0 mt-1">
      <div
        v-for="conv in conversations"
        :key="conv.id"
        :class="[
          'group flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm cursor-pointer transition-all duration-150',
          conv.id === activeConversationId
            ? 'bg-white text-gray-800 shadow-sm border border-[#e8e0d6]'
            : 'text-gray-500 hover:bg-[#ebe6e0] hover:text-gray-700 border border-transparent'
        ]"
        @click="switchTo(conv.id)"
      >
        <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
        </svg>
        <span class="flex-1 truncate">{{ conv.title || '新对话' }}</span>

        <div class="relative" @click.stop>
          <button
            class="opacity-0 group-hover:opacity-100 p-0.5 rounded text-gray-400 hover:text-gray-600 hover:bg-[#e0d9d0] transition-all"
            @click="toggleMenu(conv.id)"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z"/>
            </svg>
          </button>
          <div v-if="openMenuId === conv.id" class="absolute right-0 top-full mt-1 w-28 bg-white border border-[#e8e0d6] rounded-lg shadow-lg z-20 py-1">
            <button class="w-full text-left px-3 py-1.5 text-xs text-gray-600 hover:bg-[#f5f0eb] flex items-center gap-2" @click="startRename(conv)">✏️ 重命名</button>
            <button class="w-full text-left px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 flex items-center gap-2" @click="confirmDelete(conv)">🗑️ 删除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom nav links -->
    <nav class="p-2 space-y-0.5 shrink-0 border-t border-[#e8e0d6]">
      <router-link to="/" class="sidebar-link text-gray-500 hover:text-gray-700 hover:bg-[#ebe6e0]" :class="{ active: $route.name === 'chat' }">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
        <span>对话</span>
      </router-link>
      <router-link to="/history" class="sidebar-link text-gray-500 hover:text-gray-700 hover:bg-[#ebe6e0]" :class="{ active: $route.name === 'history' }">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <span>历史</span>
      </router-link>
      <router-link to="/settings" class="sidebar-link text-gray-500 hover:text-gray-700 hover:bg-[#ebe6e0]" :class="{ active: $route.name === 'settings' }">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
        <span>设置</span>
      </router-link>
      <router-link v-if="isAdmin" to="/admin" class="sidebar-link text-gray-500 hover:text-gray-700 hover:bg-[#ebe6e0]" :class="{ active: $route.name === 'admin' }">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
        <span>管理后台</span>
      </router-link>
    </nav>

    <!-- Status bar -->
    <div class="p-3 border-t border-[#e8e0d6] shrink-0">
      <div class="flex items-center gap-2 mb-1">
        <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
        <span class="text-xs text-gray-400 flex-1">系统正常</span>
        <span class="text-xs text-gray-500 truncate max-w-[80px]">{{ username }}</span>
      </div>
      <button class="text-[11px] text-gray-400 hover:text-gray-600 transition-colors" @click="handleLogout">退出登录</button>
    </div>

    <!-- Rename prompt -->
    <div v-if="renaming" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20" @click.self="renaming = null">
      <div class="bg-white border border-[#e8e0d6] rounded-xl p-5 w-80 mx-4 shadow-xl" @click.stop>
        <h3 class="text-sm font-semibold text-gray-700 mb-3">重命名对话</h3>
        <input ref="renameInput" v-model="renameText"
          class="w-full rounded-lg border border-[#e8e0d6] bg-white px-4 py-2.5 text-sm text-gray-700 placeholder-gray-400 outline-none focus:border-duck-400 focus:ring-2 focus:ring-duck-200 transition-all"
          placeholder="输入新名称" maxlength="200"
          @keydown.enter="doRename" @keydown.escape="renaming = null" />
        <div class="flex gap-2 mt-4 justify-end">
          <button class="px-3 py-1.5 rounded-lg text-gray-500 text-sm hover:bg-[#f5f0eb] hover:text-gray-700 transition-all" @click="renaming = null">取消</button>
          <button class="px-4 py-1.5 rounded-lg bg-duck-500 text-white font-medium text-sm hover:bg-duck-600 transition-all shadow-sm" @click="doRename">确认</button>
        </div>
      </div>
    </div>

    <!-- Delete confirm -->
    <div v-if="deleting" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20" @click.self="deleting = null">
      <div class="bg-white border border-[#e8e0d6] rounded-xl p-5 w-80 mx-4 shadow-xl" @click.stop>
        <h3 class="text-sm font-semibold text-gray-700 mb-2">删除对话</h3>
        <p class="text-xs text-gray-400 mb-4">此操作将永久删除该对话及其所有消息，无法恢复。</p>
        <div class="flex gap-2 justify-end">
          <button class="px-3 py-1.5 rounded-lg text-gray-500 text-sm hover:bg-[#f5f0eb] hover:text-gray-700 transition-all" @click="deleting = null">取消</button>
          <button class="text-xs py-1.5 px-4 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-all shadow-sm" @click="doDelete">确认删除</button>
        </div>
      </div>
    </div>
  </component>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { useConversations } from '@/composables/useConversations'

const props = defineProps({ mobile: { type: Boolean, default: false } })
const emit = defineEmits(['close', 'new-chat', 'switch-conv'])
const router = useRouter()
const route = useRoute()
const { username, isAdmin, clearAuth } = useAuth()
const { conversations, activeConversationId, loadConversations, createConversation, renameConversation, deleteConversation, setActive } = useConversations()
const openMenuId = ref(null), renaming = ref(null), renameText = ref(''), renameInput = ref(null), deleting = ref(null)

onMounted(() => { loadConversations() })
watch(openMenuId, (val) => { if (val) { const h = () => { openMenuId.value = null; document.removeEventListener('click', h) }; setTimeout(() => document.addEventListener('click', h), 0) } })
watch(() => route.path, () => { openMenuId.value = null })

function toggleMenu(id) { openMenuId.value = openMenuId.value === id ? null : id }
async function handleNewChat() {
  openMenuId.value = null; const m = sessionStorage.getItem('duck_last_model') || ''
  if (!m) { setActive(''); emit('new-chat'); if (props.mobile) emit('close'); return }
  try { await createConversation(m); emit('new-chat'); if (props.mobile) emit('close') } catch (e) { console.error(e) }
}
async function switchTo(id) { if (openMenuId.value) { openMenuId.value = null; return }; setActive(id); emit('switch-conv'); if (props.mobile) emit('close') }
function startRename(conv) { openMenuId.value = null; renaming.value = conv; renameText.value = conv.title || ''; nextTick(() => { renameInput.value?.focus(); renameInput.value?.select() }) }
async function doRename() { if (!renaming.value || !renameText.value.trim()) return; await renameConversation(renaming.value.id, renameText.value.trim()); renaming.value = null }
function confirmDelete(conv) { openMenuId.value = null; deleting.value = conv }
async function doDelete() { if (!deleting.value) return; await deleteConversation(deleting.value.id); deleting.value = null; emit('switch-conv') }
function handleLogout() { clearAuth() }
</script>
