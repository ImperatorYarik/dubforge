<script setup>
import { ref, onMounted, watch } from 'vue'
import { getStreamUrl } from '@/api/videos'
import SkeletonBlock from '@/components/SkeletonBlock.vue'

const props = defineProps({
  videoId: { type: String, required: true },
  poster:  { type: String, default: null },
})

const streamUrl = ref(null)
const error = ref(false)
const loading = ref(true)

async function load() {
  loading.value = true
  error.value = false
  try {
    const { data } = await getStreamUrl(props.videoId)
    streamUrl.value = data.url
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.videoId, load)
</script>

<template>
  <div class="video-wrap">
    <SkeletonBlock v-if="loading" width="100%" height="280px" radius="var(--radius-lg)" />
    <div v-else-if="error" class="error-state">
      Could not load video.
    </div>
    <video
      v-else-if="streamUrl"
      :src="streamUrl"
      :poster="poster ?? undefined"
      controls
      preload="metadata"
      playsinline
      class="player"
      @error="error = true"
    />
  </div>
</template>

<style scoped>
.video-wrap {
  width: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: #0A0A0A;
}
.player {
  width: 100%;
  max-height: 340px;
  display: block;
  background: #000;
}
.error-state {
  padding: 48px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>


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
