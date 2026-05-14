<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="h-14 flex items-center gap-2 px-4 border-b border-slate-800 shrink-0 bg-slate-900/40">
      <button class="btn-ghost p-1 text-lg leading-none" @click="$router.push('/')">←</button>
      <h2 class="text-sm font-semibold text-slate-200">⚙️ 设置</h2>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6">
      <div class="max-w-xl mx-auto space-y-6">

        <!-- About -->
        <section class="rounded-xl bg-slate-900/40 border border-slate-800/60 p-5">
          <h3 class="text-sm font-semibold text-slate-200 mb-3">关于</h3>
          <div class="space-y-2 text-sm text-slate-400">
            <p>🦆 <span class="text-duck-400 font-medium">Duck Chat</span> — 基于 Ollama + OpenClaw 的 AI 聊天</p>
            <p class="flex gap-2">
              <span class="text-slate-500 w-20 shrink-0">版本</span>
              <span>1.0.0</span>
            </p>
            <p class="flex gap-2">
              <span class="text-slate-500 w-20 shrink-0">后端</span>
              <span>FastAPI + PostgreSQL</span>
            </p>
            <p class="flex gap-2">
              <span class="text-slate-500 w-20 shrink-0">前端</span>
              <span>Vue 3 + Tailwind CSS</span>
            </p>
          </div>
        </section>

        <!-- Cloud Auth -->
        <section class="rounded-xl bg-slate-900/40 border border-slate-800/60 p-5">
          <h3 class="text-sm font-semibold text-slate-200 mb-3">云端连接</h3>
          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-400">OpenClaw 云端模型</span>
            <span
              class="text-xs px-2 py-1 rounded-full"
              :class="isAuthed ? 'bg-emerald-900/40 text-emerald-400 border border-emerald-800/50' : 'bg-slate-800 text-slate-500 border border-slate-700'"
            >
              {{ isAuthed ? '✅ 已连接' : '🔒 未连接' }}
            </span>
          </div>
          <button v-if="isAuthed" class="mt-3 btn-ghost text-red-400 hover:text-red-300 hover:bg-red-900/20" @click="logout">
            断开连接
          </button>
        </section>

        <!-- Stats -->
        <section class="rounded-xl bg-slate-900/40 border border-slate-800/60 p-5">
          <h3 class="text-sm font-semibold text-slate-200 mb-3">使用统计</h3>
          <div v-if="usage" class="grid grid-cols-2 gap-3">
            <div class="bg-slate-800/50 rounded-lg p-3 text-center">
              <p class="text-2xl font-semibold text-duck-400">{{ usage.total_messages || 0 }}</p>
              <p class="text-xs text-slate-500 mt-1">总消息数</p>
            </div>
            <div class="bg-slate-800/50 rounded-lg p-3 text-center">
              <p class="text-2xl font-semibold text-duck-400">{{ usage.total_tokens || 0 }}</p>
              <p class="text-xs text-slate-500 mt-1">消耗 Tokens</p>
            </div>
          </div>
          <p v-else class="text-sm text-slate-500">暂无统计</p>
        </section>

        <!-- Account -->
        <section class="rounded-xl bg-slate-900/40 border border-slate-800/60 p-5">
          <h3 class="text-sm font-semibold text-slate-200 mb-3">账户</h3>
          <p class="text-sm text-slate-400 mb-3">当前用户：{{ username }}</p>
          <button class="btn-ghost text-red-400 hover:text-red-300 hover:bg-red-900/20 border border-red-900/30 px-4 py-2 rounded-lg" @click="handleLogout">
            退出登录
          </button>
        </section>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { useCloudKey } from '@/composables/useCloudKey'
import { fetchUsage } from '@/api'

const router = useRouter()
const { username, clearAuth } = useAuth()
const { isAuthed, logout, load } = useCloudKey()
const usage = ref(null)

onMounted(async () => {
  try {
    usage.value = await fetchUsage()
  } catch {}
})

function handleLogout() {
  clearAuth()
}
</script>
