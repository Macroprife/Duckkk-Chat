<template>
  <div class="flex flex-col h-full bg-[#f7f5f2]">
    <div class="h-14 flex items-center gap-2 px-4 border-b border-[#e8e4df] shrink-0 bg-white">
      <button class="btn-ghost p-1 text-lg leading-none" @click="$router.push('/')">←</button>
      <h2 class="text-sm font-semibold text-gray-700">⚙️ 管理后台</h2>
    </div>

    <div class="flex gap-1 px-4 pt-3 pb-1 border-b border-[#e8e4df] shrink-0 bg-[#f7f5f2]">
      <button v-for="tab in tabs" :key="tab.key"
        class="px-4 py-2 text-xs rounded-t-lg transition-all"
        :class="activeTab === tab.key ? 'bg-white text-gray-700 border border-b-0 border-[#e8e4df] font-medium' : 'text-gray-400 hover:text-gray-600 hover:bg-white/50'"
        @click="activeTab = tab.key"
      >{{ tab.label }}</button>
    </div>

    <div class="flex-1 overflow-y-auto p-4">
      <!-- Stats -->
      <div v-if="activeTab === 'stats'" class="max-w-3xl mx-auto">
        <div v-if="statsLoading" class="text-center text-gray-400 py-12">加载中...</div>
        <div v-else>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <div class="bg-white border border-[#e8e4df] rounded-xl p-4 text-center shadow-sm">
              <p class="text-2xl font-bold text-duck-600">{{ stats.total_users || 0 }}</p>
              <p class="text-xs text-gray-400 mt-1">总用户</p>
            </div>
            <div class="bg-white border border-[#e8e4df] rounded-xl p-4 text-center shadow-sm">
              <p class="text-2xl font-bold text-duck-600">{{ stats.total_conversations || 0 }}</p>
              <p class="text-xs text-gray-400 mt-1">总对话</p>
            </div>
            <div class="bg-white border border-[#e8e4df] rounded-xl p-4 text-center shadow-sm">
              <p class="text-2xl font-bold text-duck-600">{{ stats.total_messages || 0 }}</p>
              <p class="text-xs text-gray-400 mt-1">总消息</p>
            </div>
            <div class="bg-white border border-[#e8e4df] rounded-xl p-4 text-center shadow-sm">
              <p class="text-2xl font-bold text-duck-600">{{ formatTokens(stats.total_tokens || 0) }}</p>
              <p class="text-xs text-gray-400 mt-1">总 Tokens</p>
            </div>
          </div>

          <h3 class="text-sm font-semibold text-gray-700 mb-3">最近使用记录</h3>
          <div v-if="recentUsage.length === 0" class="text-sm text-gray-400 text-center py-6">暂无记录</div>
          <div v-else class="space-y-1">
            <div v-for="r in recentUsage" :key="r.id"
              class="flex items-center gap-3 px-3 py-2 rounded-lg bg-white border border-[#e8e4df] text-xs shadow-sm">
              <span class="text-duck-600 font-medium w-28 truncate">{{ r.model_id }}</span>
              <span class="text-gray-400 w-16">{{ r.provider }}</span>
              <span class="text-gray-500">📝 {{ r.tokens_prompt || 0 }} / {{ r.tokens_completion || 0 }}</span>
              <span v-if="r.duration_ms" class="text-gray-400 ml-auto">{{ (r.duration_ms / 1000).toFixed(1) }}s</span>
              <span class="text-gray-400 ml-auto">{{ formatTime(r.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Users -->
      <div v-if="activeTab === 'users'" class="max-w-4xl mx-auto">
        <div v-if="usersLoading" class="text-center text-gray-400 py-12">加载中...</div>
        <div v-else>
          <p class="text-xs text-gray-400 mb-3">共 {{ usersTotal }} 个用户</p>
          <div class="space-y-1">
            <div v-for="u in users" :key="u.id"
              class="flex items-center gap-3 px-4 py-3 rounded-xl bg-white border border-[#e8e4df] shadow-sm">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-medium text-gray-700">{{ u.username }}</span>
                  <span class="text-xs px-1.5 py-0.5 rounded" :class="u.role === 'admin' ? 'bg-purple-50 text-purple-600 border border-purple-200' : 'bg-gray-100 text-gray-400 border border-gray-200'">{{ u.role }}</span>
                  <span v-if="!u.is_active" class="text-xs px-1.5 py-0.5 rounded bg-red-50 text-red-500 border border-red-200">已封禁</span>
                </div>
                <p class="text-xs text-gray-400 mt-0.5">注册于 {{ formatTime(u.created_at) }}</p>
              </div>
              <div class="flex gap-1 shrink-0">
                <button class="text-xs px-2 py-1 rounded border transition-all"
                  :class="u.role === 'admin' ? 'border-purple-200 text-purple-500 hover:bg-purple-50' : 'border-gray-200 text-gray-400 hover:text-gray-600 hover:bg-gray-100'"
                  @click="toggleRole(u)">{{ u.role === 'admin' ? '取消管理' : '设为管理' }}</button>
                <button class="text-xs px-2 py-1 rounded border transition-all"
                  :class="u.is_active ? 'border-red-200 text-red-500 hover:bg-red-50' : 'border-emerald-200 text-emerald-600 hover:bg-emerald-50'"
                  @click="toggleBan(u)">{{ u.is_active ? '封禁' : '解封' }}</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const router = useRouter()
const { isAdmin } = useAuth()

const tabs = [
  { key: 'stats', label: '📊 数据统计' },
  { key: 'users', label: '👥 用户管理' },
]
const activeTab = ref('stats')
const statsLoading = ref(true)
const stats = ref({})
const recentUsage = ref([])
const usersLoading = ref(true)
const users = ref([])
const usersTotal = ref(0)

onMounted(() => {
  if (!isAdmin.value) { router.push('/'); return }
  loadStats(); loadUsers()
})

async function loadStats() {
  try {
    const r = await fetch('/api/admin/stats', { credentials: 'include' })
    const data = await r.json()
    if (data.ok) { stats.value = data.stats || {}; recentUsage.value = data.recent_usage || [] }
  } catch (e) { console.error('load stats error', e) }
  finally { statsLoading.value = false }
}

async function loadUsers() {
  try {
    const r = await fetch('/api/admin/users?limit=100', { credentials: 'include' })
    const data = await r.json()
    if (data.ok) { users.value = data.users || []; usersTotal.value = data.total || 0 }
  } catch (e) { console.error('load users error', e) }
  finally { usersLoading.value = false }
}

async function toggleRole(u) {
  try {
    await fetch(`/api/admin/users/${u.id}/role`, { method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role: u.role === 'admin' ? 'user' : 'admin' }) })
    u.role = u.role === 'admin' ? 'user' : 'admin'
  } catch (e) { console.error('toggle role error', e) }
}

async function toggleBan(u) {
  try {
    await fetch(`/api/admin/users/${u.id}/ban`, { method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ is_active: !u.is_active }) })
    u.is_active = !u.is_active
  } catch (e) { console.error('toggle ban error', e) }
}

function formatTokens(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n
}

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>
