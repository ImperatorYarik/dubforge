<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useVideosStore } from '@/stores/videos'
import { useJobsStore } from '@/stores/jobs'
import { useToast } from '@/composables/useToast'
import VideoPlayer from '@/components/VideoPlayer.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import MediaAssetsPanel from '@/components/studio/MediaAssetsPanel.vue'
import StudioTimeline from '@/components/studio/StudioTimeline.vue'
import AiDubbingPanel from '@/components/studio/AiDubbingPanel.vue'

const route = useRoute()
const projectsStore = useProjectsStore()
const videosStore = useVideosStore()
const jobsStore = useJobsStore()
const toast = useToast()

const activeTopTab = ref('editor') // 'editor' | 'export'
const activeVideoId = ref(null)
const currentTime = ref(0)
const duration = ref(0)
const progressPct = ref(0)
const progressMsg = ref('')
const isGenerating = ref(false)
const dubbedVideoId = ref(null)

const projectId = computed(() => route.params.projectId)

const project = computed(() =>
  projectsStore.projects.find(p => p.project_id === projectId.value) || null
)

const projectVideos = computed(() =>
  videosStore.videosForProject(projectId.value)
)

const displayVideoId = computed(() => dubbedVideoId.value || activeVideoId.value)

onMounted(async () => {
  await Promise.all([
    projectsStore.fetchProject(projectId.value),
    videosStore.fetchVideos(),
  ])
  // Auto-select first video
  if (projectVideos.value.length > 0 && !activeVideoId.value) {
    activeVideoId.value = projectVideos.value[0].video_id
  }
})

onUnmounted(() => {
  jobsStore.disconnectWS()
})

function handleSelectVideo(videoId) {
  activeVideoId.value = videoId
  dubbedVideoId.value = null
}

function handleSeek(time) {
  currentTime.value = time
}

async function handleGenerateDub(options) {
  if (!activeVideoId.value) {
    toast.warn('Select a video asset first.')
    return
  }

  isGenerating.value = true
  progressPct.value = 0
  progressMsg.value = 'Starting...'
  dubbedVideoId.value = null

  try {
    const result = await jobsStore.dub(
      projectId.value,
      activeVideoId.value,
      options,
      (progress) => {
        progressPct.value = progress.pct ?? progressPct.value
        progressMsg.value = progress.message ?? progressMsg.value
      }
    )

    if (result?.dubbed_video_id) {
      dubbedVideoId.value = result.dubbed_video_id
    }

    toast.success('Dub complete!')
    // Refresh video list to get updated dubbed_url
    await videosStore.fetchVideos()
  } catch {
    toast.error(jobsStore.error || 'Dubbing failed.')
  } finally {
    isGenerating.value = false
    progressPct.value = 0
    progressMsg.value = ''
  }
}
</script>

<template>
  <div class="dubbing-studio">
    <!-- Top Bar -->
    <header class="dubbing-studio__topbar" data-testid="studio-topbar">
      <div class="dubbing-studio__project-info">
        <span class="dubbing-studio__project-name">
          {{ project?.title || 'Loading...' }}
        </span>
      </div>

      <div class="dubbing-studio__tabs">
        <button
          class="dubbing-studio__tab"
          :class="{ 'dubbing-studio__tab--active': activeTopTab === 'editor' }"
          data-testid="tab-editor"
          @click="activeTopTab = 'editor'"
        >
          Editor
        </button>
        <button
          class="dubbing-studio__tab"
          :class="{ 'dubbing-studio__tab--active': activeTopTab === 'export' }"
          data-testid="tab-export"
          @click="activeTopTab = 'export'"
        >
          Export
        </button>
      </div>

      <div class="dubbing-studio__topbar-actions">
        <button class="btn btn-primary btn-sm" data-testid="btn-export">
          Export Video
        </button>
      </div>
    </header>

    <!-- Progress bar under topbar -->
    <div v-if="isGenerating" class="dubbing-studio__progress-bar">
      <div
        class="dubbing-studio__progress-fill"
        :style="{ width: `${progressPct}%` }"
      />
      <span class="dubbing-studio__progress-msg">{{ progressMsg }}</span>
    </div>

    <!-- Main workspace -->
    <div class="dubbing-studio__workspace">
      <!-- Left: Media Assets -->
      <aside class="dubbing-studio__left" data-testid="media-assets-panel">
        <MediaAssetsPanel
          :videos="projectVideos"
          :active-video-id="activeVideoId"
          @select-video="handleSelectVideo"
        />
      </aside>

      <!-- Center: Player + Timeline -->
      <main class="dubbing-studio__center">
        <div class="dubbing-studio__player-wrap" data-testid="video-player-area">
          <template v-if="displayVideoId">
            <VideoPlayer :video-id="displayVideoId" />
            <!-- Timecode / status overlay -->
            <div class="dubbing-studio__overlay">
              <span class="dubbing-studio__timecode">
                {{ String(Math.floor(currentTime / 3600)).padStart(2, '0') }}:{{ String(Math.floor((currentTime % 3600) / 60)).padStart(2, '0') }}:{{ String(Math.floor(currentTime % 60)).padStart(2, '0') }}:00
              </span>
              <span v-if="dubbedVideoId" class="dubbing-studio__badge">
                Dubbed
              </span>
            </div>
          </template>
          <div v-else class="dubbing-studio__no-video">
            <SkeletonBlock v-if="videosStore.loading" width="100%" height="100%" radius="0" />
            <div v-else class="dubbing-studio__no-video-msg">
              Select a video from the media panel
            </div>
          </div>
        </div>

        <div class="dubbing-studio__timeline-wrap" data-testid="studio-timeline">
          <StudioTimeline
            :video-id="activeVideoId"
            :dubbed-video-id="dubbedVideoId"
            :duration="duration"
            :current-time="currentTime"
            @seek="handleSeek"
          />
        </div>
      </main>

      <!-- Right: AI Dubbing Panel -->
      <aside class="dubbing-studio__right" data-testid="ai-dubbing-panel">
        <AiDubbingPanel
          :loading="isGenerating"
          @generate-dub="handleGenerateDub"
        />
      </aside>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/scss/views/DubbingStudioView';
</style>
