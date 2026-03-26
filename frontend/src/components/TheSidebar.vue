<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useJobsStore } from '@/stores/jobs'

const route = useRoute()
const projectsStore = useProjectsStore()
const jobsStore = useJobsStore()

const showProjectPicker = ref(false)

const currentProject = computed(() => projectsStore.currentProject)

function selectProject(id) {
  projectsStore.setCurrentProject(id)
  showProjectPicker.value = false
}

const recentJobs = computed(() => jobsStore.recentJobs.slice(0, 8))
const activeJobs = computed(() => jobsStore.recentJobs.filter(j => j.state === 'STARTED' || j.state === 'PENDING'))

function jobTypeLabel(type) {
  return { dub: 'Dubbing', transcribe: 'Transcription', separate: 'Separation' }[type] ?? type
}

function jobStateColor(state) {
  if (state === 'STARTED') return 'var(--amber)'
  if (state === 'SUCCESS') return 'var(--teal)'
  if (state === 'FAILURE') return 'var(--red)'
  return 'var(--dim)'
}

function fmtTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

let _pollTimer = null
onMounted(async () => {
  await jobsStore.fetchRecentJobs()
  _pollTimer = setInterval(() => jobsStore.fetchRecentJobs(), 5000)
})
onBeforeUnmount(() => clearInterval(_pollTimer))

const pipelineNav = [
  {
    label: 'Dubbing',
    to: '/dub',
    icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>`,
  },
  {
    label: 'Transcription',
    to: '/transcribe',
    icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>`,
  },
  {
    label: 'Text to Speech',
    to: '/tts',
    icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>`,
  },
]

const manageNav = [
  {
    label: 'Projects',
    to: '/projects',
    icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>`,
  },
  {
    label: 'Voices',
    to: '/voices',
    icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>`,
  },
]
</script>

<template>
  <aside class="sidebar">
    <div class="logo">
      <RouterLink to="/projects" class="logo-link">
        <span class="logo-dub">Dub</span><span class="logo-forge">Forge</span>
      </RouterLink>
    </div>

    <div class="nav-section">
      <span class="section-label">TOOLS</span>
      <nav class="nav">
        <RouterLink
          v-for="item in pipelineNav"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ active: route.path === item.to }"
        >
          <span class="nav-icon" v-html="item.icon"></span>
          <span class="nav-label">{{ item.label }}</span>
        </RouterLink>
      </nav>
    </div>

    <div class="nav-section">
      <span class="section-label">MANAGE</span>
      <nav class="nav">
        <RouterLink
          v-for="item in manageNav"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ active: route.path.startsWith(item.to) }"
        >
          <span class="nav-icon" v-html="item.icon"></span>
          <span class="nav-label">{{ item.label }}</span>
        </RouterLink>
      </nav>
    </div>

    <!-- Recent Jobs -->
    <div v-if="recentJobs.length" class="nav-section jobs-section">
      <span class="section-label">
        JOBS
        <span v-if="activeJobs.length" class="jobs-badge">{{ activeJobs.length }}</span>
      </span>
      <div class="jobs-list">
        <div
          v-for="job in recentJobs"
          :key="job.task_id"
          class="job-item"
          :class="{ running: job.state === 'STARTED' }"
        >
          <div class="job-row">
            <span class="job-dot" :style="{ background: jobStateColor(job.state) }"></span>
            <span class="job-type">{{ jobTypeLabel(job.type) }}</span>
            <span class="job-time">{{ fmtTime(job.submitted_at) }}</span>
          </div>
          <div v-if="job.state === 'STARTED'" class="job-progress">
            <div class="job-bar">
              <div class="job-fill" :style="{ width: (job.pct || 0) + '%' }"></div>
            </div>
            <span class="job-pct">{{ job.pct || 0 }}%</span>
          </div>
          <div v-if="job.message && job.state === 'STARTED'" class="job-msg">{{ job.message }}</div>
        </div>
      </div>
    </div>

    <div class="sidebar-bottom">
      <span class="section-label project-chip-label">ACTIVE PROJECT</span>
      <button class="project-chip" @click="showProjectPicker = !showProjectPicker">
        <span class="chip-dot" :class="currentProject ? 'dot-active' : 'dot-none'"></span>
        <span class="chip-name">{{ currentProject?.metadata?.title || 'No project' }}</span>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
      </button>

      <!-- Project Picker Dropdown -->
      <div v-if="showProjectPicker" class="project-picker">
        <div class="picker-header">
          <span class="section-label">SELECT PROJECT</span>
          <RouterLink to="/projects" class="picker-new" @click="showProjectPicker = false">+ New</RouterLink>
        </div>
        <div v-if="!projectsStore.projects.length" class="picker-empty">No projects yet</div>
        <button
          v-for="p in projectsStore.projects"
          :key="p.project_id"
          class="picker-item"
          :class="{ selected: p.project_id === projectsStore.currentProjectId }"
          @click="selectProject(p.project_id)"
        >
          {{ p.metadata?.title || 'Untitled' }}
        </button>
      </div>
    </div>
  </aside>
</template>


<style scoped lang="scss">
@use './TheSidebar';
</style>
