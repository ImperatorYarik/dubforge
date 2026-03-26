<script setup>
import { ref, onMounted } from 'vue'
import { useVideosStore } from '@/stores/videos'
import { useToast } from '@/composables/useToast'
import VideoCard from '@/components/VideoCard.vue'
import { useJobsStore } from '@/stores/jobs'

const store = useVideosStore()
const jobsStore = useJobsStore()
const toast = useToast()

const selectedFile = ref(null)
const projectId = ref('')
const uploading = ref(false)
const showForm = ref(false)

onMounted(() => store.fetchVideos())

function onFileChange(e) {
  selectedFile.value = e.target.files[0] ?? null
}

async function handleUpload() {
  if (!selectedFile.value || !projectId.value.trim()) return
  uploading.value = true
  try {
    await store.uploadVideo(selectedFile.value, projectId.value.trim())
    toast.success('Video uploaded successfully!')
    selectedFile.value = null
    projectId.value = ''
    showForm.value = false
  } catch {
    toast.error(store.error ?? 'Upload failed')
  } finally {
    uploading.value = false
  }
}

async function handleTranscribe(video) {
  try {
    const job = await jobsStore.transcribe(video.project_id, video.video_id)
    toast.success(`Transcription queued (task: ${job.task_id})`)
  } catch {
    toast.error(jobsStore.error ?? 'Failed to start transcription')
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>Videos</h1>
      <button class="btn btn-primary" @click="showForm = !showForm">
        {{ showForm ? 'Cancel' : '+ Upload Video' }}
      </button>
    </div>

    <transition name="slide">
      <form v-if="showForm" class="card form-card" @submit.prevent="handleUpload">
        <h2>Upload Video File</h2>
        <div class="field">
          <label for="project-id">Project ID</label>
          <input
            id="project-id"
            v-model="projectId"
            type="text"
            placeholder="Enter project ID"
            required
          />
        </div>
        <div class="field">
          <label for="video-file">Video File</label>
          <input id="video-file" type="file" accept="video/*" required @change="onFileChange" />
        </div>
        <button type="submit" class="btn btn-primary" :disabled="uploading">
          {{ uploading ? 'Uploading…' : 'Upload' }}
        </button>
      </form>
    </transition>

    <div v-if="store.loading" class="loading">Loading videos…</div>
    <div v-else-if="store.error" class="error-msg">{{ store.error }}</div>
    <div v-else-if="store.videos.length === 0" class="empty">No videos uploaded yet.</div>
    <div v-else class="video-list">
      <VideoCard
        v-for="v in store.videos"
        :key="v.video_id"
        :video="v"
        :transcribing="jobsStore.loading"
        @transcribe="handleTranscribe(v)"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
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

.video-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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
