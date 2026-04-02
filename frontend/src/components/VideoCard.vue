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

<style scoped lang="scss">@use '../assets/scss/components/VideoCard';</style>
