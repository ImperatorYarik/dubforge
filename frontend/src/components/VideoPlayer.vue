<script setup>
import { ref, onMounted } from 'vue'
import { getStreamUrl } from '@/api/videos'

const props = defineProps({
  videoId: {
    type: String,
    required: true,
  },
  /** Optional poster/thumbnail image URL */
  poster: {
    type: String,
    default: null,
  },
})

const streamUrl = ref(null)
const error = ref(false)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await getStreamUrl(props.videoId)
    streamUrl.value = data.url
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
})

function onError() {
  error.value = true
}
</script>

<template>
  <div class="video-player">
    <div v-if="loading" class="player-loading">Loading…</div>
    <div v-else-if="error" class="player-error">
      <span>⚠️ Could not load video.</span>
    </div>
    <video
      v-else-if="streamUrl"
      :src="streamUrl"
      :poster="poster ?? undefined"
      controls
      preload="metadata"
      playsinline
      class="player"
      @error="onError"
    >
      Your browser does not support the video tag.
    </video>
  </div>
</template>

<style scoped>
.video-player {
  width: 100%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.player {
  width: 100%;
  max-height: 480px;
  display: block;
  background: #000;
}

.player-loading,
.player-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2.5rem;
  color: #aaa;
  font-size: 0.9rem;
}
</style>
