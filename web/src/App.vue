<template>
  <div class="h-dvh flex bg-slate-950 text-slate-200">
    <template v-if="authed">
      <Sidebar />
      <main class="flex-1 flex flex-col min-w-0">
        <router-view />
      </main>
    </template>
    <div v-else-if="checking" class="flex-1 flex items-center justify-center">
      <span class="text-slate-500">验证会话...</span>
    </div>
    <LoginGate v-else @authed="onAuthed" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuth } from '@/composables/useAuth'
import Sidebar from '@/components/Sidebar.vue'
import LoginGate from '@/components/LoginGate.vue'

const { authed, checkSession } = useAuth()
const checking = ref(true)

onMounted(async () => {
  // Verify token hasn't been invalidated by another login
  await checkSession()
  checking.value = false
})

function onAuthed() {
  // Reactivity handles the rest
}
</script>
