<template>
  <div class="flex flex-col h-full bg-[#f7f5f2]">
    <!-- Header -->
    <div class="h-14 flex items-center gap-2 px-4 border-b border-[#e8e4df] shrink-0 bg-white">
      <button class="btn-ghost p-1 text-lg leading-none" @click="$router.push('/')">←</button>
      <h2 class="text-sm font-semibold text-gray-700">⚙️ 设置</h2>
    </div>

    <div class="flex-1 overflow-y-auto p-6">
      <div class="max-w-xl mx-auto space-y-6">

        <!-- About -->
        <section class="rounded-xl bg-white border border-[#e8e4df] p-5 shadow-sm">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">关于</h3>
          <div class="space-y-2 text-sm text-gray-500">
            <p><img src="/duck-icon.svg" alt="Duck" class="w-5 h-5 inline-block align-middle" /> <span class="text-duck-600 font-medium">Duck Chat</span> — 基于 Ollama + OpenClaw 的 AI 聊天</p>
            <p class="flex gap-2"><span class="text-gray-400 w-20 shrink-0">版本</span><span>1.0.0</span></p>
            <p class="flex gap-2"><span class="text-gray-400 w-20 shrink-0">后端</span><span>FastAPI + PostgreSQL</span></p>
            <p class="flex gap-2"><span class="text-gray-400 w-20 shrink-0">前端</span><span>Vue 3 + Tailwind CSS</span></p>
          </div>
        </section>

        <!-- Cloud Auth -->
        <section class="rounded-xl bg-white border border-[#e8e4df] p-5 shadow-sm">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">云端连接</h3>
          <div class="flex items-center justify-between">
            <span class="text-sm text-gray-500">OpenClaw 云端模型</span>
            <span class="text-xs px-2 py-1 rounded-full" :class="isAuthed ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'bg-gray-100 text-gray-400 border border-gray-200'">
              {{ isAuthed ? '✅ 已连接' : '🔒 未连接' }}
            </span>
          </div>
          <button v-if="isAuthed" class="mt-3 btn-ghost text-red-500 hover:text-red-600 hover:bg-red-50" @click="logout">断开连接</button>
        </section>

        <!-- Stats -->
        <section class="rounded-xl bg-white border border-[#e8e4df] p-5 shadow-sm">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">使用统计</h3>
          <div v-if="usage" class="grid grid-cols-2 gap-3">
            <div class="bg-[#f7f5f2] rounded-lg p-3 text-center border border-[#e8e4df]">
              <p class="text-2xl font-semibold text-duck-600">{{ usage.total_messages || 0 }}</p>
              <p class="text-xs text-gray-400 mt-1">总消息数</p>
            </div>
            <div class="bg-[#f7f5f2] rounded-lg p-3 text-center border border-[#e8e4df]">
              <p class="text-2xl font-semibold text-duck-600">{{ usage.total_tokens || 0 }}</p>
              <p class="text-xs text-gray-400 mt-1">消耗 Tokens</p>
            </div>
          </div>
          <p v-else class="text-sm text-gray-400">暂无统计</p>
        </section>

        <!-- Account -->
        <section class="rounded-xl bg-white border border-[#e8e4df] p-5 shadow-sm">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">账户</h3>
          <p class="text-sm text-gray-500 mb-3">当前用户：{{ username }}</p>
          <button class="btn-ghost text-red-500 hover:text-red-600 hover:bg-red-50 border border-red-200 px-4 py-2 rounded-lg" @click="handleLogout">退出登录</button>
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
const { isAuthed, logout } = useCloudKey()
const usage = ref(null)

onMounted(async () => { try { usage.value = await fetchUsage() } catch {} })
function handleLogout() { clearAuth() }
</script>
