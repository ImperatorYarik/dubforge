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
    <SkeletonBlock v-if="loading" width="100%" height="100%" radius="0" />
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

<style scoped lang="scss">
.video-wrap {
  width: 100%;
  height: 100%;
  background: #000;
}

.player {
  width: 100%;
  height: 100%;
  max-height: 100%;
  display: block;
  object-fit: contain;
  background: #000;
}

.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: rgb(255,255,255,0.35);
  font-size: 13px;
}
</style>
