<template>
  <aside class="w-60 bg-slate-900/80 border-r border-slate-800 flex flex-col shrink-0 hidden md:flex">
    <!-- Logo -->
    <div class="h-14 flex items-center gap-2 px-4 border-b border-slate-800">
      <span class="text-xl">🦆</span>
      <span class="font-semibold text-duck-400">Duck</span>
      <span class="text-slate-300 font-semibold">Chat</span>
    </div>

    <!-- Nav -->
    <nav class="flex-1 p-2 space-y-1">
      <router-link to="/" class="sidebar-link" :class="{ active: $route.name === 'chat' }">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
        <span>对话</span>
      </router-link>
      <router-link to="/history" class="sidebar-link" :class="{ active: $route.name === 'history' }">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <span>历史</span>
      </router-link>
      <router-link to="/settings" class="sidebar-link" :class="{ active: $route.name === 'settings' }">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
        <span>设置</span>
      </router-link>
    </nav>

    <!-- Bottom status -->
    <div class="p-3 border-t border-slate-800 text-xs text-slate-500 flex items-center gap-2">
      <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
      系统正常
    </div>
  </aside>
</template>
