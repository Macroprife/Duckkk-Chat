<template>
  <div class="h-dvh flex bg-gray-50 text-gray-800">
    <template v-if="authed">
      <Sidebar />
      <main class="flex-1 flex flex-col min-w-0">
        <router-view />
      </main>
    </template>
    <div v-else-if="checking" class="flex-1 flex items-center justify-center">
      <span class="text-gray-400">验证会话...</span>
    </div>
    <LoginGate v-else @authed="onAuthed" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuth } from '@/composables/useAuth'
import Sidebar from '@/components/Sidebar.vue'
import LoginGate from '@/components/LoginGate.vue'

const { authed, checkSession } = useAuth()
const checking = ref(true)
let _heartbeat = null

onMounted(async () => {
  await checkSession()
  checking.value = false
  // 每隔 60 秒校验 session 是否被其他地方登出或改密码
  _heartbeat = setInterval(async () => {
    await checkSession()
  }, 60000)
})

onUnmounted(() => {
  if (_heartbeat) clearInterval(_heartbeat)
})

function onAuthed() {}
</script>
