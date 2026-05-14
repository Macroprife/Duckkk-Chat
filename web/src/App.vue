<template>
  <div class="h-dvh flex bg-slate-950 text-slate-200">
    <Sidebar />
    <main class="flex-1 flex flex-col min-w-0">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import Sidebar from '@/components/Sidebar.vue'
</script>
