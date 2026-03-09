<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useVideosStore } from '@/stores/videos'
import { useJobsStore } from '@/stores/jobs'
import { useToast } from '@/composables/useToast'
import VideoPlayer from '@/components/VideoPlayer.vue'
import TranscriptPanel from '@/components/TranscriptPanel.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import { proxyVideoUrl } from '@/utils/url'

const route  = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()
const videosStore   = useVideosStore()
const jobsStore     = useJobsStore()
const toast = useToast()

const dubbedDirectUrl = ref(null)
const translatedSegs  = ref([])
const isProcessing    = ref(false)
const progressPct     = ref(0)
const progressMsg     = ref('')

// Transcription state
const transcription   = ref('')         // plain text from MongoDB
const translateMode   = ref(false)      // toggle: translate or just transcribe

onMounted(async () => {
  await Promise.all([
    projectsStore.fetchProject(route.params.id),
    videosStore.fetchVideos(),
  ])
  if (sourceVideo.value?.transcription) {
    transcription.value = sourceVideo.value.transcription
  }
})

const project = computed(() => projectsStore.currentProject)

const sourceVideo = computed(() =>
  videosStore.videosForProject(route.params.id)[0] ?? null
)

function onProgress({ pct, message }) {
  progressPct.value = pct
  progressMsg.value = message
}

async function generateTranscription() {
  if (!sourceVideo.value) return
  isProcessing.value = true
  progressPct.value  = 0
  progressMsg.value  = 'Starting…'
  transcription.value = ''
  try {
    await jobsStore.transcribe(
      route.params.id,
      sourceVideo.value.video_id,
      translateMode.value,
      onProgress,
    )
    // Fetch the single video to get the updated transcription from MongoDB
    const updated = await videosStore.fetchVideo(sourceVideo.value.video_id)
    transcription.value = updated?.transcription ?? ''
    toast.success('Transcription complete')
  } catch (e) {
    toast.error('Transcription failed: ' + e.message)
  } finally {
    isProcessing.value = false
    progressPct.value  = 0
    progressMsg.value  = ''
  }
}

async function generateDub() {
  if (!sourceVideo.value) return
  isProcessing.value = true
  progressPct.value  = 0
  progressMsg.value  = 'Starting…'
  dubbedDirectUrl.value = null
  translatedSegs.value  = []
  try {
    const result = await jobsStore.dub(
      route.params.id,
      sourceVideo.value.video_id,
      onProgress,
    )
    if (result?.dubbed_url) {
      dubbedDirectUrl.value = result.dubbed_url
    }
    if (result?.transcript_url) {
      try {
        const res = await fetch(proxyVideoUrl(result.transcript_url))
        const txt = await res.text()
        translatedSegs.value = txt.split('\n').filter(l => l.trim()).map(l => {
          const m = l.match(/\[(\d+\.\d+)s - (\d+\.\d+)s\] (.+)/)
          return m ? { start: parseFloat(m[1]), end: parseFloat(m[2]), text: m[3] } : null
        }).filter(Boolean)
      } catch { /* transcript fetch failed silently */ }
    }
    toast.success('Dubbing complete')
  } catch (e) {
    toast.error('Dubbing failed: ' + e.message)
  } finally {
    isProcessing.value = false
    progressPct.value  = 0
    progressMsg.value  = ''
  }
}
</script>

<template>
  <div class="workspace">
    <!-- Toolbar -->
    <div class="toolbar">
      <button class="btn btn-ghost btn-sm" @click="router.push({ name: 'projects' })">
        ← Projects
      </button>

      <template v-if="project">
        <span class="proj-title">{{ project.metadata?.title || 'Untitled' }}</span>
      </template>

      <!-- Progress bar (shown during any job) -->
      <div v-if="isProcessing" class="progress-wrap">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPct + '%' }" />
        </div>
        <span class="progress-label">{{ progressMsg || 'Processing…' }} {{ progressPct }}%</span>
      </div>

      <!-- Transcribe controls -->
      <div class="transcribe-group">
        <label class="translate-toggle" :class="{ active: translateMode }">
          <input type="checkbox" v-model="translateMode" :disabled="isProcessing" />
          Translate
        </label>
        <button
          class="btn btn-secondary btn-sm"
          :disabled="isProcessing || !sourceVideo"
          @click="generateTranscription"
        >
          <span v-if="isProcessing && progressMsg.includes('ranscri')" class="spinner" />
          Transcribe
        </button>
      </div>

      <button
        class="btn btn-primary fab"
        :disabled="isProcessing || !sourceVideo"
        @click="generateDub"
      >
        <span v-if="isProcessing && !progressMsg.includes('ranscri')" class="spinner" />
        Generate Dub →
      </button>
    </div>

    <!-- Loading project -->
    <div v-if="projectsStore.loading" class="panes">
      <div class="pane">
        <SkeletonBlock width="100%" height="340px" radius="var(--radius-lg)" />
        <div class="transcript-head">
          <SkeletonBlock width="120px" height="14px" style="margin-top:24px" />
        </div>
      </div>
      <div class="pane">
        <SkeletonBlock width="100%" height="340px" radius="var(--radius-lg)" />
      </div>
    </div>

    <!-- Dual pane workspace -->
    <div v-else class="panes">
      <!-- LEFT: original -->
      <div class="pane">
        <div class="pane-label">Original</div>
        <div v-if="sourceVideo" class="player-wrap">
          <VideoPlayer :video-id="sourceVideo.video_id" />
        </div>
        <div v-else class="empty-player">No video uploaded yet.</div>

        <div class="transcript-head">
          <span class="pane-label">Transcript</span>
        </div>
        <div class="transcript-scroll">
          <template v-if="isProcessing && progressMsg.includes('ranscri')">
            <TranscriptPanel :segments="[]" :loading="true" />
          </template>
          <div v-else-if="transcription" class="transcription-text">
            <p v-for="(line, i) in transcription.split('\n').filter(l => l.trim())" :key="i">{{ line }}</p>
          </div>
          <div v-else class="empty-transcript">
            No transcript yet — click <strong>Transcribe</strong> to generate one.
          </div>
        </div>
      </div>

      <!-- RIGHT: dubbed -->
      <div class="pane">
        <div class="pane-label">Translation</div>

        <!-- Processing state -->
        <template v-if="isProcessing && !progressMsg.includes('ranscri')">
          <SkeletonBlock width="100%" height="340px" radius="var(--radius-lg)" />
          <div class="processing-hint">{{ progressMsg || 'Processing…' }}</div>
        </template>

        <!-- Dubbed video -->
        <template v-else-if="dubbedDirectUrl">
          <div class="player-wrap">
            <video
              :src="proxyVideoUrl(dubbedDirectUrl)"
              controls
              class="dubbed-player"
            />
          </div>
        </template>

        <!-- Idle placeholder -->
        <div v-else class="empty-player idle">
          <p>Dubbed video will appear here.</p>
          <p class="hint">Click <strong>Generate Dub →</strong> to start.</p>
        </div>

        <div class="transcript-head">
          <span class="pane-label">Translated Script</span>
        </div>
        <div class="transcript-scroll">
          <TranscriptPanel
            :segments="translatedSegs"
            :loading="isProcessing && !progressMsg.includes('ranscri')"
            :editable="true"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.workspace {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* ---- Toolbar ---- */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
}
.proj-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.fab { margin-left: auto; }

/* ---- Progress ---- */
.progress-wrap {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 160px;
}
.progress-bar {
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--color-accent, #6366f1);
  border-radius: 2px;
  transition: width 0.3s ease;
}
.progress-label {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

/* ---- Transcribe group ---- */
.transcribe-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
.translate-toggle {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
  padding: 4px 8px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--surface);
  transition: border-color 0.15s, color 0.15s;
}
.translate-toggle.active {
  border-color: var(--color-accent, #6366f1);
  color: var(--color-accent, #6366f1);
}
.translate-toggle input { accent-color: var(--color-accent, #6366f1); }

/* ---- Panes ---- */
.panes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  flex: 1;
  overflow: hidden;
}

.pane {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--border);
  padding: 20px;
  gap: 0;
}
.pane:last-child { border-right: none; }

.pane-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.player-wrap {
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: 0;
}

.dubbed-player {
  width: 100%;
  max-height: 340px;
  display: block;
  background: #000;
  border-radius: var(--radius-lg);
}

.empty-player {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 280px;
  border: 1.5px dashed var(--border);
  border-radius: var(--radius-lg);
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
  gap: 8px;
}
.idle { background: var(--surface-subtle); }
.hint { font-size: 12px; color: var(--text-placeholder); }

.processing-hint {
  text-align: center;
  color: var(--text-muted);
  font-size: 12.5px;
  padding: 10px 0;
}

.transcript-head {
  display: flex;
  align-items: center;
  padding: 16px 0 8px;
  flex-shrink: 0;
}

.transcript-scroll {
  flex: 1;
  overflow-y: auto;
}

.transcription-text {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text);
}
.transcription-text p {
  margin: 0 0 6px;
}

.empty-transcript {
  font-size: 13px;
  color: var(--text-muted);
  padding: 16px 0;
}

/* ---- Spinner ---- */
.spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: rgba(255,255,255,0.9);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
