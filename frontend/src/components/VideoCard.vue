<script setup>
import { ref } from 'vue'
import VideoPlayer from '@/components/VideoPlayer.vue'

defineProps({
  video: {
    type: Object,
    required: true,
  },
  transcribing: {
    type: Boolean,
    default: false,
  },
  /** Optional thumbnail passed through from project metadata */
  poster: {
    type: String,
    default: null,
  },
})

defineEmits(['transcribe'])

const playerOpen = ref(false)

function formatDate(iso) {
  return new Date(iso).toLocaleString()
}

function shortPath(url) {
  try {
    return new URL(url).pathname.split('/').pop()
  } catch {
    return url
  }
}
</script>

<template>
  <div class="card video-card">
    <!-- Header row -->
    <div class="video-header">
      <div class="video-info">
        <div class="icon">🎥</div>
        <div class="details">
          <p class="filename" :title="video.video_url">{{ shortPath(video.video_url) }}</p>
          <p class="muted small">Project: {{ video.project_id }}</p>
          <p class="muted small">{{ formatDate(video.created_at) }}</p>
        </div>
      </div>
      <div class="actions">
        <button class="btn btn-secondary" @click="playerOpen = !playerOpen">
          {{ playerOpen ? 'Hide' : '▶ Play' }}
        </button>
        <button
          class="btn btn-primary"
          :disabled="transcribing"
          @click="$emit('transcribe')"
        >
          {{ transcribing ? 'Queuing…' : 'Transcribe' }}
        </button>
      </div>
    </div>

    <!-- Inline video player -->
    <transition name="expand">
      <div v-if="playerOpen" class="player-wrap">
        <VideoPlayer :video-id="video.video_id" :poster="poster" />
      </div>
    </transition>
  </div>
</template>

<style scoped>
.video-card {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.video-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.video-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
}

.icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.details {
  min-width: 0;
}

.filename {
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 360px;
  margin: 0 0 0.2rem;
}

.small {
  font-size: 0.78rem;
}

.actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.player-wrap {
  margin-top: 1rem;
  border-radius: 8px;
  overflow: hidden;
}

/* Expand animation */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}
.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 520px;
}
</style>
