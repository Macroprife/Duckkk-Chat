import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    proxy: {
      '/models': 'http://127.0.0.1:8000',
      '/chat': 'http://127.0.0.1:8000',
      '/auth': 'http://127.0.0.1:8000',
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router'],
          markdown: ['marked', 'highlight.js'],
        },
      },
    },
    chunkSizeWarningLimit: 400,
  },
})
