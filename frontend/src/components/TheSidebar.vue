<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useJobsStore } from '@/stores/jobs'

const route = useRoute()
const router = useRouter()
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
  return { dub: 'Dub', transcribe: 'Transcribe', separate: 'Separate' }[type] ?? type
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
      <span class="section-label">PIPELINES</span>
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

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  min-height: 100vh;
  height: 100vh;
  position: sticky;
  top: 0;
  background: var(--bg2);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;
}

.logo {
  padding: 18px 16px 12px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 8px;
}
.logo-link {
  font-family: var(--font-display);
  font-size: 22px;
  letter-spacing: 0.04em;
  color: var(--text);
}
.logo-dub { color: var(--amber); }
.logo-forge { color: var(--text); }

.nav-section {
  padding: 12px 12px 4px;
}
.section-label {
  display: block;
  padding: 0 6px 8px;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 10px;
  border-radius: var(--radius);
  font-size: 13px;
  font-family: var(--font-body);
  font-weight: 400;
  color: var(--muted);
  transition: background 0.1s, color 0.1s;
  border: 1px solid transparent;
}
.nav-link:hover {
  background: var(--bg4);
  color: var(--text);
}
.nav-link.active {
  background: var(--amber-g);
  color: var(--amber);
  border-color: var(--b-amber);
}

.nav-icon {
  width: 16px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Jobs section */
.jobs-section { flex-shrink: 0; }
.jobs-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--amber);
  color: #000;
  font-size: 9px;
  font-weight: 700;
  border-radius: 8px;
  padding: 1px 5px;
  margin-left: 5px;
  line-height: 1.4;
}
.jobs-list { display: flex; flex-direction: column; gap: 2px; }
.job-item {
  padding: 6px 8px;
  border-radius: var(--radius);
  background: var(--bg3);
  border: 1px solid var(--border);
  font-size: 11px;
}
.job-item.running { border-color: var(--b-amber); background: var(--amber-g); }
.job-row { display: flex; align-items: center; gap: 6px; }
.job-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.job-type { flex: 1; color: var(--text); font-family: var(--font-mono); font-size: 11px; }
.job-time { color: var(--dim); font-family: var(--font-mono); font-size: 10px; }
.job-progress { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
.job-bar { flex: 1; height: 3px; background: var(--bg4); border-radius: 2px; overflow: hidden; }
.job-fill { height: 100%; background: var(--amber); border-radius: 2px; transition: width 0.3s; }
.job-pct { font-family: var(--font-mono); font-size: 10px; color: var(--amber); min-width: 26px; text-align: right; }
.job-msg { margin-top: 2px; color: var(--muted); font-size: 10px; font-family: var(--font-mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Bottom project chip */
.sidebar-bottom {
  margin-top: auto;
  padding: 12px;
  border-top: 1px solid var(--border);
  position: relative;
}

.project-chip {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--radius);
  background: var(--bg3);
  border: 1px solid var(--border);
  color: var(--text);
  font-size: 12px;
  font-family: var(--font-mono);
  cursor: pointer;
  transition: border-color 0.1s;
}
.project-chip:hover { border-color: var(--b-amber); }

.chip-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-active { background: var(--teal); }
.dot-none { background: var(--dim); }

.chip-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

/* Project Picker */
.project-picker {
  position: absolute;
  bottom: calc(100% + 4px);
  left: 12px;
  right: 12px;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 8px;
  z-index: 100;
  max-height: 260px;
  overflow-y: auto;
}

.picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 6px 8px;
}
.picker-new {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--amber);
}
.picker-new:hover { text-decoration: underline; }

.picker-empty {
  padding: 12px 8px;
  font-size: 12px;
  color: var(--muted);
  text-align: center;
}

.picker-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 8px 10px;
  border-radius: var(--radius);
  font-size: 12px;
  font-family: var(--font-body);
  color: var(--text);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.1s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.picker-item:hover { background: var(--bg4); }
.picker-item.selected {
  color: var(--amber);
  border-color: var(--b-amber);
  background: var(--amber-g);
}
</style>
