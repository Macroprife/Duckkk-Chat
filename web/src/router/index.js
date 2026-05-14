import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '@/views/ChatView.vue'
import HistoryView from '@/views/HistoryView.vue'
import SettingsView from '@/views/SettingsView.vue'

const routes = [
  { path: '/',           name: 'chat',    component: ChatView },
  { path: '/history',    name: 'history', component: HistoryView },
  { path: '/settings',   name: 'settings', component: SettingsView },
]

const router = createRouter({
  history: createWebHistory('/'),
  routes,
})

export default router
