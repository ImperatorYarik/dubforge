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
    router.push({ name: 'project-detail', params: { id: project.project_id } })
  } catch {
    toast.error('Failed to upload video')
  } finally {
    uploading.value = false
  }
}

async function onYoutubeSubmit() {
  if (!youtubeUrl.value) return
  try {
    const project = await store.createProject(youtubeUrl.value, true)
    toast.success('Project created')
    showCreate.value = false
    youtubeUrl.value = ''
    router.push({ name: 'project-detail', params: { id: project.project_id } })
  } catch {
    toast.error('Failed to create project')
  }
}

async function onBlankSubmit() {
  if (!newProjectName.value.trim()) return
  try {
    const project = await store.createBlankProject(newProjectName.value.trim())
    toast.success('Project created')
    showCreate.value = false
    newProjectName.value = ''
    router.push({ name: 'project-detail', params: { id: project.project_id } })
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

function getStatusLabel(project) {
  if (project.dubbed_url || project.has_dubbed) return 'Complete'
  if (project.is_processing) return 'Processing'
  return 'Draft'
}
</script>

<template>
  <div class="projects-view">

    <!-- Page header -->
    <div class="projects-view__header">
      <div class="projects-view__heading">
        <h1 class="projects-view__title">Projects</h1>
        <p class="projects-view__subtitle">Manage your video dubbing projects</p>
      </div>
      <button
        class="btn btn-primary"
        data-testid="new-project-btn"
        @click="showCreate = !showCreate"
      >
        + New Project
      </button>
    </div>

    <!-- Create panel -->
    <div v-if="showCreate" class="projects-view__create-panel" data-testid="create-panel">
      <div class="projects-view__create-tabs">
        <button
          :class="['projects-view__create-tab', { 'projects-view__create-tab--active': createMode === 'file' }]"
          data-testid="tab-file"
          @click="createMode = 'file'"
        >
          Upload File
        </button>
        <button
          :class="['projects-view__create-tab', { 'projects-view__create-tab--active': createMode === 'youtube' }]"
          data-testid="tab-youtube"
          @click="createMode = 'youtube'"
        >
          YouTube URL
        </button>
        <button
          :class="['projects-view__create-tab', { 'projects-view__create-tab--active': createMode === 'blank' }]"
          data-testid="tab-blank"
          @click="createMode = 'blank'"
        >
          Blank Project
        </button>
      </div>

      <!-- File upload dropzone -->
      <div
        v-if="createMode === 'file'"
        class="projects-view__dropzone"
        :class="{
          'projects-view__dropzone--dragover': isDragOver,
          'projects-view__dropzone--uploading': uploading,
        }"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
        @click="$refs.fileInput.click()"
      >
        <input
          ref="fileInput"
          type="file"
          accept="video/*"
          style="display:none"
          @change="e => handleFile(e.target.files[0])"
        />
        <div v-if="uploading" class="projects-view__dz-uploading">
          <div class="projects-view__spinner"></div>
          Creating project…
        </div>
        <div v-else class="projects-view__dz-idle">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/>
            <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
          </svg>
          <p class="projects-view__dz-title">Drop a video file here</p>
          <p class="projects-view__dz-sub">A new project will be created automatically</p>
        </div>
      </div>

      <!-- YouTube URL -->
      <div v-if="createMode === 'youtube'" class="projects-view__form-row">
        <input
          class="input"
          v-model="youtubeUrl"
          placeholder="https://youtube.com/watch?v=…"
          @keyup.enter="onYoutubeSubmit"
        />
        <button
          class="btn btn-primary"
          :disabled="!youtubeUrl"
          @click="onYoutubeSubmit"
        >
          Create from YouTube
        </button>
      </div>

      <!-- Blank project -->
      <div v-if="createMode === 'blank'" class="projects-view__form-row">
        <input
          class="input"
          v-model="newProjectName"
          placeholder="Project name"
          @keyup.enter="onBlankSubmit"
        />
        <button
          class="btn btn-primary"
          :disabled="!newProjectName.trim()"
          @click="onBlankSubmit"
        >
          Create
        </button>
      </div>
    </div>

    <!-- Search bar — shown only when projects exist -->
    <div v-if="!store.loading && store.projects.length > 0" class="projects-view__search">
      <input
        class="input projects-view__search-input"
        v-model="searchQuery"
        placeholder="Search projects…"
        data-testid="search-input"
      />
    </div>

    <!-- Loading skeletons -->
    <div v-if="store.loading" class="projects-view__grid">
      <div
        v-for="n in 6"
        :key="n"
        class="projects-view__card projects-view__card--skeleton"
      >
        <div class="projects-view__card-thumb">
          <SkeletonBlock width="100%" height="100%" />
        </div>
        <div class="projects-view__card-body">
          <SkeletonBlock width="70%" height="14px" />
          <SkeletonBlock width="40%" height="11px" style="margin-top: 6px" />
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="!store.projects.length"
      class="projects-view__empty"
      data-testid="empty-state"
    >
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.25">
        <rect x="2" y="3" width="20" height="14" rx="2"/>
        <line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
      </svg>
      <p class="projects-view__empty-title">No projects yet</p>
      <p class="projects-view__empty-sub">Create your first project to start dubbing or transcribing</p>
      <button class="btn btn-primary btn-sm" @click="showCreate = true">+ Create Project</button>
    </div>

    <!-- No search results -->
    <div v-else-if="searchQuery && !filteredProjects.length" class="projects-view__empty">
      <p class="projects-view__empty-title">No results for "{{ searchQuery }}"</p>
      <p class="projects-view__empty-sub">Try a different search term</p>
    </div>

    <!-- Project grid -->
    <div v-else class="projects-view__grid">
      <div
        v-for="p in filteredProjects"
        :key="p.project_id"
        class="projects-view__card"
        :class="{ 'projects-view__card--active': p.project_id === store.currentProjectId }"
        data-testid="project-card"
        @click="selectProject(p.project_id)"
      >
        <div class="projects-view__card-thumb">
          <img v-if="p.metadata?.thumbnail" :src="p.metadata.thumbnail" alt="" />
          <div v-else class="projects-view__card-thumb-fallback">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </div>
        </div>

        <div class="projects-view__card-body">
          <p class="projects-view__card-title">{{ p.metadata?.title || 'Untitled' }}</p>
          <p class="projects-view__card-date">{{ formatDate(p.created_at) }}</p>
        </div>

        <div class="projects-view__card-actions">
          <span
            class="projects-view__status-pill"
            :class="`projects-view__status-pill--${getStatusLabel(p).toLowerCase()}`"
          >
            {{ getStatusLabel(p) }}
          </span>
          <button
            class="projects-view__delete-btn"
            title="Delete project"
            data-testid="delete-project-btn"
            @click.stop="onDeleteProject($event, p.project_id)"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped lang="scss">
@use '../assets/scss/views/ProjectsView';
</style>
