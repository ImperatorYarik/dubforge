<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useToast } from '@/composables/useToast'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import * as videosApi from '@/api/videos'

const router = useRouter()
const store = useProjectsStore()
const toast = useToast()

const showCreate = ref(false)
const uploading = ref(false)
const youtubeUrl = ref('')
const newProjectName = ref('')
const createMode = ref('file')  // 'file' | 'youtube' | 'blank'
const isDragOver = ref(false)
const searchQuery = ref('')

const filteredProjects = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return store.projects
  return store.projects.filter(p =>
    (p.metadata?.title || 'Untitled').toLowerCase().includes(q)
  )
})

onMounted(() => store.fetchProjects())

async function onDeleteProject(event, projectId) {
  event.stopPropagation()
  if (!confirm('Delete this project? This cannot be undone.')) return
  try {
    await store.deleteProject(projectId)
    toast.success('Project deleted')
  } catch {
    toast.error('Failed to delete project')
  }
}

function onDragOver(e) { e.preventDefault(); isDragOver.value = true }
function onDragLeave() { isDragOver.value = false }
function onDrop(e) {
  e.preventDefault()
  isDragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('video/')) handleFile(file)
}

async function handleFile(file) {
  uploading.value = true
  try {
    const title = file.name.replace(/\.[^/.]+$/, '')
    const project = await store.createBlankProject(title)
    await videosApi.uploadVideo(file, project.project_id)
    toast.success('Project created')
    showCreate.value = false
    router.push({ name: 'dub' })
  } catch {
    toast.error('Failed to upload video')
  } finally {
    uploading.value = false
  }
}

async function onYoutubeSubmit() {
  if (!youtubeUrl.value) return
  try {
    await store.createProject(youtubeUrl.value, true)
    toast.success('Project created')
    showCreate.value = false
    youtubeUrl.value = ''
    router.push({ name: 'dub' })
  } catch {
    toast.error('Failed to create project')
  }
}

async function onBlankSubmit() {
  if (!newProjectName.value.trim()) return
  try {
    await store.createBlankProject(newProjectName.value.trim())
    toast.success('Project created')
    showCreate.value = false
    newProjectName.value = ''
  } catch {
    toast.error('Failed to create project')
  }
}

function selectProject(id) {
  store.setCurrentProject(id)
  router.push({ name: 'project-detail', params: { id } })
}

function formatDate(d) {
  const date = new Date(d)
  const now = new Date()
  const diffDays = Math.floor((now - date) / 86400000)
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

<template>
  <div class="view">
    <div class="page-header">
      <div>
        <h1 class="page-title">Projects</h1>
        <p class="page-sub">Select a project to begin dubbing or transcription</p>
      </div>
      <button class="btn btn-primary" @click="showCreate = !showCreate">
        + New Project
      </button>
    </div>

    <!-- Create Panel -->
    <div v-if="showCreate" class="create-panel">
      <div class="create-tabs">
        <button :class="['tab', { active: createMode === 'file' }]" @click="createMode = 'file'">Upload File</button>
        <button :class="['tab', { active: createMode === 'youtube' }]" @click="createMode = 'youtube'">YouTube URL</button>
        <button :class="['tab', { active: createMode === 'blank' }]" @click="createMode = 'blank'">Blank Project</button>
      </div>

      <!-- File upload -->
      <div
        v-if="createMode === 'file'"
        class="dropzone"
        :class="{ dragover: isDragOver, uploading }"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
        @click="$refs.fileInput.click()"
      >
        <input ref="fileInput" type="file" accept="video/*" style="display:none" @change="e => handleFile(e.target.files[0])" />
        <div v-if="uploading" class="dz-hint">Creating project…</div>
        <div v-else class="dz-idle">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>
          <p class="dz-title">Drop a video file</p>
          <p class="dz-sub">A new project will be created automatically</p>
        </div>
      </div>

      <!-- YouTube -->
      <div v-if="createMode === 'youtube'" class="form-group">
        <input class="input" v-model="youtubeUrl" placeholder="https://youtube.com/watch?v=…" />
        <button class="btn btn-primary" @click="onYoutubeSubmit" :disabled="!youtubeUrl">Create from YouTube</button>
      </div>

      <!-- Blank -->
      <div v-if="createMode === 'blank'" class="form-group">
        <input class="input" v-model="newProjectName" placeholder="Project name" @keyup.enter="onBlankSubmit" />
        <button class="btn btn-primary" @click="onBlankSubmit" :disabled="!newProjectName.trim()">Create</button>
      </div>
    </div>

    <!-- Search -->
    <div v-if="!store.loading && store.projects.length > 0" class="search-row">
      <input
        class="input search-input"
        v-model="searchQuery"
        placeholder="Search projects…"
      />
    </div>

    <!-- Project list -->
    <div class="projects-list">
      <template v-if="store.loading">
        <div class="project-card skeleton-card" v-for="n in 4" :key="n">
          <SkeletonBlock width="100%" height="16px" />
          <SkeletonBlock width="80px" height="11px" style="margin-top:8px" />
        </div>
      </template>

      <div v-else-if="!store.projects.length" class="empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.3"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        <p class="empty-title">No projects yet</p>
        <p class="empty-sub">Create your first project to start dubbing or transcribing</p>
        <button class="btn btn-primary btn-sm" @click="showCreate = true">+ Create Project</button>
      </div>

      <div v-else-if="searchQuery && !filteredProjects.length" class="empty">
        <p class="empty-title">No results for "{{ searchQuery }}"</p>
        <p class="empty-sub">Try a different search term</p>
      </div>

      <div
        v-else
        v-for="p in filteredProjects"
        :key="p.project_id"
        class="project-card"
        :class="{ current: p.project_id === store.currentProjectId }"
        @click="selectProject(p.project_id)"
      >
        <div class="card-thumb">
          <img v-if="p.metadata?.thumbnail" :src="p.metadata.thumbnail" alt="" />
          <div v-else class="thumb-fallback">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          </div>
        </div>
        <div class="card-body">
          <p class="card-name">{{ p.metadata?.title || 'Untitled' }}</p>
          <p class="card-date">{{ formatDate(p.created_at) }}</p>
        </div>
        <div class="card-actions">
          <span v-if="p.project_id === store.currentProjectId" class="badge badge-ok">Active</span>
          <button class="action-btn" title="Delete" @click.stop="onDeleteProject($event, p.project_id)">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">@use '../assets/scss/views/ProjectsView';</style>
