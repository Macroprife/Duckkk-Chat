<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" @click.self="$emit('close')">
      <div class="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-80 shadow-2xl fade-in">
        <h3 class="text-lg font-semibold mb-1">🔒 连接云端</h3>
        <p class="text-sm text-slate-400 mb-4">输入云端密钥以解锁 OpenClaw 模型</p>
        <input
          ref="inputRef"
          v-model="key"
          type="password"
          class="input-field mb-4"
          placeholder="输入密钥..."
          @keydown.enter="submit"
        />
        <div class="flex gap-2 justify-end">
          <button class="btn-ghost" @click="$emit('close')">取消</button>
          <button class="btn-primary" :disabled="!key.trim()" @click="submit">连接</button>
        </div>
        <p v-if="error" class="mt-3 text-sm text-red-400">{{ error }}</p>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['close', 'auth'])
const key = ref('')
const error = ref('')
const inputRef = ref(null)

onMounted(() => {
  inputRef.value?.focus()
})

async function submit() {
  if (!key.value.trim()) return
  error.value = ''
  emit('auth', key.value.trim())
}
</script>
