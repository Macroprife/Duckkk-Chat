<template>
  <div class="h-14 flex items-center gap-3 px-4 border-b border-slate-800 shrink-0 bg-slate-900/40">
    <!-- Mobile menu trigger -->
    <button class="md:hidden btn-ghost text-lg p-1" @click="$emit('toggle-mobile-menu')">☰</button>

    <div class="flex items-center gap-2">
      <ModelSelector
        :providers="providers"
        :current="currentModel"
        :loading="loading"
        @change="$emit('model-change', $event)"
      />
    </div>

    <div class="ml-auto flex items-center gap-2">
      <button
        class="btn-ghost flex items-center gap-1.5"
        :class="cloudAuthed ? 'text-emerald-400 border border-emerald-800/50' : ''"
        @click="$emit('toggle-cloud')"
      >
        <span v-if="cloudAuthed">✅</span>
        <span v-else>🔒</span>
        <span class="hidden sm:inline">{{ cloudAuthed ? '已连接' : '云端' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import ModelSelector from './ModelSelector.vue'

defineProps({
  providers: Array,
  currentModel: String,
  loading: Boolean,
  cloudAuthed: Boolean,
})

defineEmits(['toggle-cloud', 'model-change', 'toggle-mobile-menu'])
</script>
