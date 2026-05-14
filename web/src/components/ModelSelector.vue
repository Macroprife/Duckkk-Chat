<template>
  <select
    class="bg-slate-900 text-slate-200 border border-slate-700 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-duck-400/60 cursor-pointer min-w-[140px]"
    :value="current"
    :disabled="loading"
    @change="$emit('change', $event.target.value)"
  >
    <option value="" disabled v-if="loading">加载中...</option>
    <optgroup v-for="g in providers" :key="g.provider" :label="g.provider">
      <option
        v-for="m in g.models"
        :key="m.id"
        :value="m.id"
      >{{ m.name }}{{ m.size ? ` (${m.size})` : '' }}{{ m.cloud ? ' ☁️' : '' }}</option>
    </optgroup>
  </select>
</template>

<script setup>
defineProps({
  providers: Array,
  current: String,
  loading: Boolean,
})
defineEmits(['change'])
</script>
