<script setup>
import { ref, onMounted } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useToast } from '@/composables/useToast'
import ProjectCard from '@/components/ProjectCard.vue'

const store = useProjectsStore()
const toast = useToast()

const youtubeUrl = ref('')
const downloadFromYoutube = ref(true)
const submitting = ref(false)
const showForm = ref(false)

onMounted(() => store.fetchProjects())

async function handleCreate() {
  if (!youtubeUrl.value.trim()) return
  submitting.value = true
  try {
    await store.createProject(youtubeUrl.value.trim(), downloadFromYoutube.value)
    toast.success('Project created successfully!')
    youtubeUrl.value = ''
    showForm.value = false
  } catch {
    toast.error(store.error ?? 'Failed to create project')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>Projects</h1>
      <button class="btn btn-primary" @click="showForm = !showForm">
        {{ showForm ? 'Cancel' : '+ New Project' }}
      </button>
    </div>

    <transition name="slide">
      <form v-if="showForm" class="card form-card" @submit.prevent="handleCreate">
        <h2>Create from YouTube</h2>
        <div class="field">
          <label for="yt-url">YouTube URL</label>
          <input
            id="yt-url"
            v-model="youtubeUrl"
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            required
          />
        </div>
        <div class="field checkbox-field">
          <input id="download" v-model="downloadFromYoutube" type="checkbox" />
          <label for="download">Download video automatically</label>
        </div>
        <button type="submit" class="btn btn-primary" :disabled="submitting">
          {{ submitting ? 'Creating…' : 'Create Project' }}
        </button>
      </form>
    </transition>

    <div v-if="store.loading" class="loading">Loading projects…</div>
    <div v-else-if="store.error" class="error-msg">{{ store.error }}</div>
    <div v-else-if="store.projects.length === 0" class="empty">
      No projects yet. Create one from a YouTube URL above.
    </div>
    <div v-else class="grid">
      <ProjectCard v-for="p in store.projects" :key="p.project_id" :project="p" />
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.form-card {
  margin-bottom: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.checkbox-field {
  flex-direction: row;
  align-items: center;
  gap: 0.6rem;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.25rem;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
