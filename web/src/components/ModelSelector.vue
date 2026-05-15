<template>
  <select
    class="bg-white text-gray-700 border border-gray-300 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-duck-400 focus:ring-2 focus:ring-duck-200 cursor-pointer min-w-[140px] shadow-sm"
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
      >{{ m.name }}{{ m.size ? ` (${m.size})` : '' }}</option>
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
