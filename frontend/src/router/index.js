import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dub' },
  {
    path: '/dub',
    name: 'dub',
    component: () => import('@/views/DubbingView.vue'),
    meta: { title: 'Dubbing', requiresProject: true },
  },
  {
    path: '/transcribe',
    name: 'transcribe',
    component: () => import('@/views/TranscriptionView.vue'),
    meta: { title: 'Transcription', requiresProject: true },
  },
  {
    path: '/tts',
    name: 'tts',
    component: () => import('@/views/TextToSpeechView.vue'),
    meta: { title: 'Text to Speech', requiresProject: true },
  },
  {
    path: '/projects',
    name: 'projects',
    component: () => import('@/views/ProjectsView.vue'),
    meta: { title: 'Projects' },
  },
  {
    path: '/projects/:id',
    name: 'project-detail',
    component: () => import('@/views/ProjectDetailView.vue'),
    meta: { title: 'Project' },
  },
  {
    path: '/voices',
    name: 'voices',
    component: () => import('@/views/VoicesView.vue'),
    meta: { title: 'Voices' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach(async (to) => {
  if (to.meta.requiresProject) {
    const { useProjectsStore } = await import('@/stores/projects')
    const { useToast } = await import('@/composables/useToast')
    const store = useProjectsStore()
    if (!store.currentProjectId) {
      useToast().info('Select a project to continue.')
      return { name: 'projects' }
    }
  }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} — DubForge` : 'DubForge'
})

export default router
