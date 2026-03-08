<script setup>
import { onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useVideosStore } from '@/stores/videos'
import { useJobsStore } from '@/stores/jobs'
import { useToast } from '@/composables/useToast'
import VideoCard from '@/components/VideoCard.vue'

const route = useRoute()
const projectsStore = useProjectsStore()
const videosStore = useVideosStore()
const jobsStore = useJobsStore()
const toast = useToast()

const projectId = route.params.id
const project = computed(() => projectsStore.currentProject)
const projectVideos = computed(() => videosStore.videosForProject(projectId))

onMounted(async () => {
  await Promise.all([
    projectsStore.fetchProject(projectId),
    videosStore.fetchVideos(),
  ])
})

async function handleTranscribe(videoId) {
  try {
    const job = await jobsStore.transcribe(projectId, videoId)
    toast.success(`Transcription job queued (task id: ${job.task_id})`)
  } catch {
    toast.error(jobsStore.error ?? 'Failed to start transcription')
  }
}

function formatDate(iso) {
  return new Date(iso).toLocaleString()
}
</script>

<template>
  <div class="page">
    <router-link to="/projects" class="back-link">← Back to Projects</router-link>

    <div v-if="projectsStore.loading" class="loading">Loading project…</div>
    <div v-else-if="!project" class="error-msg">Project not found.</div>
    <template v-else>
      <div class="card project-header">
        <div class="meta-row">
          <img
            v-if="project.metadata?.thumbnail"
            :src="project.metadata.thumbnail"
            :alt="project.metadata?.title"
            class="thumbnail"
          />
          <div>
            <h1>{{ project.metadata?.title ?? 'Untitled Project' }}</h1>
            <p class="muted">ID: {{ project.project_id }}</p>
            <p v-if="project.metadata?.uploader" class="muted">
              {{ project.metadata.uploader }}
            </p>
            <p v-if="project.metadata?.duration" class="muted">
              Duration: {{ project.metadata.duration }}s
            </p>
            <p class="muted">Created: {{ formatDate(project.created_at) }}</p>
          </div>
        </div>
        <p v-if="project.metadata?.description" class="description">
          {{ project.metadata.description }}
        </p>
      </div>

      <h2 class="section-title">Videos</h2>
      <div v-if="videosStore.loading" class="loading">Loading videos…</div>
      <div v-else-if="projectVideos.length === 0" class="empty">
        No videos linked to this project yet.
      </div>
      <div v-else class="video-list">
        <VideoCard
          v-for="v in projectVideos"
          :key="v.video_id"
          :video="v"
          :poster="project.metadata?.thumbnail ?? null"
          :transcribing="jobsStore.loading"
          @transcribe="handleTranscribe(v.video_id)"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.back-link {
  display: inline-block;
  margin-bottom: 1.25rem;
  color: var(--color-accent);
  text-decoration: none;
  font-size: 0.9rem;
}
.back-link:hover {
  text-decoration: underline;
}

.project-header {
  margin-bottom: 2rem;
}

.meta-row {
  display: flex;
  gap: 1.25rem;
  align-items: flex-start;
}

.thumbnail {
  width: 180px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
}

h1 {
  margin: 0 0 0.4rem;
  font-size: 1.5rem;
}

.description {
  margin-top: 1rem;
  color: var(--color-muted);
  font-size: 0.9rem;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.section-title {
  margin-bottom: 1rem;
}

.video-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
</style>
