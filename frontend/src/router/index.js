import { createRouter, createWebHistory } from 'vue-router'
import ProjectsView from '@/views/ProjectsView.vue'

const routes = [
  { path: '/', redirect: '/projects' },
  { path: '/projects', name: 'projects', component: ProjectsView, meta: { title: 'Projects' } },
  { path: '/projects/:id', name: 'project-detail', component: () => import('@/views/ProjectDetailView.vue'), meta: { title: 'Workspace' } },
  { path: '/voices', name: 'voices', component: () => import('@/views/VoicesView.vue'), meta: { title: 'Voices' } },
  { path: '/tts', name: 'tts', component: () => import('@/views/TextToSpeechView.vue'), meta: { title: 'Text to Speech' } },
  { path: '/settings', name: 'settings', component: () => import('@/views/SettingsView.vue'), meta: { title: 'Settings' } },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} — VideoTrans` : 'VideoTrans'
})

export default router
