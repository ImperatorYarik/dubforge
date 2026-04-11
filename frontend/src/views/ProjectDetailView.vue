<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useVideosStore } from '@/stores/videos'
import { useJobsStore } from '@/stores/jobs'
import { useToast } from '@/composables/useToast'
import VideoPlayer from '@/components/VideoPlayer.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import { getDubbedStreamUrl, getVocalsStreamUrl, getNoVocalsStreamUrl, getDubbedVersionStreamUrl, deleteDubbedVersion } from '@/api/videos'

const route  = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()
const videosStore   = useVideosStore()
const jobsStore     = useJobsStore()
const toast = useToast()

// Stream URLs
const dubbedDirectUrl   = ref(null)
const vocalsDirectUrl   = ref(null)
const noVocalsDirectUrl = ref(null)

// Segments & transcript
const translatedSegs    = ref([])
const transcription     = ref('')

// Processing state
const isProcessing      = ref(false)
const progressPct       = ref(0)
const progressMsg       = ref('')
const currentJobType    = ref(null)  // 'dub' | 'transcribe' | 'separate' | null

// UI state
const showRegenMenu     = ref(false)
const videoTab          = ref('original')  // 'original' | 'dubbed'
const selectedVersionJobId = ref(null)
const deletingVersionJobId = ref(null)
const currentSegmentIndex  = ref(-1)

// Derived data
const dubbedVersions = computed(() => sourceVideo.value?.dubbed_versions ?? [])
const sortedVersions = computed(() =>
  [...dubbedVersions.value].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
)

// Stepper derived state
const hasExtractedAudio = computed(() => !!sourceVideo.value?.vocals_url)
const hasTranscription  = computed(() => !!sourceVideo.value?.transcription || !!transcription.value)
const hasDub            = computed(() => !!sourceVideo.value?.dubbed_url || !!dubbedDirectUrl.value)

// step1: done if vocals_url, active if video exists and no vocals, locked otherwise
const step1State = computed(() => {
  if (!sourceVideo.value) return 'locked'
  if (hasExtractedAudio.value) return 'done'
  return 'active'
})

// step2: done if transcription, active if step1 done, locked otherwise
const step2State = computed(() => {
  if (hasTranscription.value) return 'done'
  if (hasExtractedAudio.value) return 'active'
  return 'locked'
})

// step3: done if dubbed_url, active if step2 done, locked otherwise
const step3State = computed(() => {
  if (hasDub.value) return 'done'
  if (hasTranscription.value) return 'active'
  return 'locked'
})

// Processing booleans
const isDubbing      = computed(() => isProcessing.value && currentJobType.value === 'dub')
const isTranscribing = computed(() => isProcessing.value && currentJobType.value === 'transcribe')
const isSeparating   = computed(() => isProcessing.value && currentJobType.value === 'separate')

// Project & video
const project = computed(() =>
  projectsStore.projects.find(p => p.project_id === route.params.id) ?? null
)
const sourceVideo = computed(() =>
  videosStore.videosForProject(route.params.id)[0] ?? null
)

function _closeRegenMenu() { showRegenMenu.value = false }
onBeforeUnmount(() => document.removeEventListener('click', _closeRegenMenu))

onMounted(async () => {
  document.addEventListener('click', _closeRegenMenu)
  await Promise.all([
    projectsStore.fetchProject(route.params.id),
    videosStore.fetchVideos(),
  ])
  if (sourceVideo.value?.transcript_segments?.length) {
    translatedSegs.value = sourceVideo.value.transcript_segments
    transcription.value = sourceVideo.value.transcription ?? ''
  } else if (sourceVideo.value?.transcription) {
    transcription.value = sourceVideo.value.transcription
    translatedSegs.value = _parseSegments(sourceVideo.value.transcription)
  }
  await _loadStreams()
})

async function _loadStreams() {
  if (!sourceVideo.value) return
  await Promise.all([
    _loadDubbedStream(),
    sourceVideo.value?.vocals_url
      ? getVocalsStreamUrl(sourceVideo.value.video_id).then(({ data }) => { vocalsDirectUrl.value = data.url }).catch(() => {})
      : Promise.resolve(),
    sourceVideo.value?.no_vocals_url
      ? getNoVocalsStreamUrl(sourceVideo.value.video_id).then(({ data }) => { noVocalsDirectUrl.value = data.url }).catch(() => {})
      : Promise.resolve(),
  ])
}

async function _loadDubbedStream() {
  if (!sourceVideo.value) return
  dubbedDirectUrl.value = null
  const jobId = selectedVersionJobId.value
  try {
    if (jobId) {
      const { data } = await getDubbedVersionStreamUrl(sourceVideo.value.video_id, jobId)
      dubbedDirectUrl.value = data.url
    } else if (sourceVideo.value?.dubbed_url) {
      const { data } = await getDubbedStreamUrl(sourceVideo.value.video_id)
      dubbedDirectUrl.value = data.url
    }
  } catch { /* no dubbed video */ }
}

async function selectVersion(jobId) {
  selectedVersionJobId.value = jobId
  await _loadDubbedStream()
  videoTab.value = 'dubbed'
}

async function deleteVersion(jobId) {
  if (!sourceVideo.value) return
  deletingVersionJobId.value = jobId
  try {
    await deleteDubbedVersion(sourceVideo.value.video_id, jobId)
    if (selectedVersionJobId.value === jobId) selectedVersionJobId.value = null
    await videosStore.fetchVideo(sourceVideo.value.video_id)
    await _loadDubbedStream()
    toast.success('Version deleted')
  } catch (e) {
    toast.error('Delete failed: ' + e.message)
  } finally {
    deletingVersionJobId.value = null
  }
}

watch(sourceVideo, (v) => { if (v) _loadStreams() })

function _parseSegments(text) {
  if (!text) return []
  return text.split('\n').filter(l => l.trim()).map(l => {
    const m = l.match(/\[(\d+\.\d+)s - (\d+\.\d+)s\] (.+)/)
    return m ? { start: parseFloat(m[1]), end: parseFloat(m[2]), text: m[3] } : null
  }).filter(Boolean)
}

function onProgress({ pct, message }) {
  progressPct.value = pct
  progressMsg.value = message
}

function fmtTimestamp(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function fmtDate(d) {
  return new Date(d).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// --- Actions ---

async function separateAudio() {
  if (!sourceVideo.value) return
  isProcessing.value = true
  currentJobType.value = 'separate'
  progressPct.value = 0
  progressMsg.value = 'Starting…'
  try {
    const result = await jobsStore.separate(
      route.params.id,
      sourceVideo.value.video_id,
      onProgress,
    )
    if (result?.vocals_url) {
      try {
        const { data } = await getVocalsStreamUrl(sourceVideo.value.video_id)
        vocalsDirectUrl.value = data.url
      } catch { vocalsDirectUrl.value = result.vocals_url }
    }
    if (result?.no_vocals_url) {
      try {
        const { data } = await getNoVocalsStreamUrl(sourceVideo.value.video_id)
        noVocalsDirectUrl.value = data.url
      } catch { noVocalsDirectUrl.value = result.no_vocals_url }
    }
    await videosStore.fetchVideo(sourceVideo.value.video_id)
    toast.success('Audio separation complete')
  } catch (e) {
    toast.error('Separation failed: ' + e.message)
  } finally {
    isProcessing.value = false
    currentJobType.value = null
    progressPct.value = 0
    progressMsg.value = ''
  }
}

async function generateTranscription() {
  if (!sourceVideo.value) return
  isProcessing.value = true
  currentJobType.value = 'transcribe'
  progressPct.value  = 0
  progressMsg.value  = 'Starting…'
  transcription.value = ''
  try {
    await jobsStore.transcribe(
      route.params.id,
      sourceVideo.value.video_id,
      true,
      onProgress,
    )
    const updated = await videosStore.fetchVideo(sourceVideo.value.video_id)
    transcription.value = updated?.transcription ?? ''
    translatedSegs.value = updated?.transcript_segments?.length
      ? updated.transcript_segments
      : _parseSegments(transcription.value)
    toast.success('Transcription complete')
  } catch (e) {
    toast.error('Transcription failed: ' + e.message)
  } finally {
    isProcessing.value = false
    currentJobType.value = null
    progressPct.value  = 0
    progressMsg.value  = ''
  }
}

async function generateDub() {
  if (!sourceVideo.value) return
  isProcessing.value = true
  currentJobType.value = 'dub'
  progressPct.value  = 0
  progressMsg.value  = 'Starting…'
  dubbedDirectUrl.value = null
  translatedSegs.value  = []
  selectedVersionJobId.value = null
  try {
    const result = await jobsStore.dub(
      route.params.id,
      sourceVideo.value.video_id,
      {},
      onProgress,
    )
    if (result?.dubbed_url) {
      try {
        const { data } = await getDubbedStreamUrl(sourceVideo.value.video_id)
        dubbedDirectUrl.value = data.url
      } catch { dubbedDirectUrl.value = result.dubbed_url }
    }
    const updated = await videosStore.fetchVideo(sourceVideo.value.video_id)
    if (updated?.transcription) {
      transcription.value = updated.transcription
      translatedSegs.value = updated?.transcript_segments?.length
        ? updated.transcript_segments
        : _parseSegments(updated.transcription)
    }
    await _loadStreams()
    videoTab.value = 'dubbed'
    toast.success('Dubbing complete')
  } catch (e) {
    toast.error('Dubbing failed: ' + e.message)
  } finally {
    isProcessing.value = false
    currentJobType.value = null
    progressPct.value  = 0
    progressMsg.value  = ''
  }
}

async function reDub() {
  showRegenMenu.value = false
  if (!sourceVideo.value) return
  isProcessing.value = true
  currentJobType.value = 'dub'
  progressPct.value  = 0
  progressMsg.value  = 'Starting…'
  dubbedDirectUrl.value = null
  translatedSegs.value  = []
  selectedVersionJobId.value = null
  try {
    const result = await jobsStore.redub(
      route.params.id,
      sourceVideo.value.video_id,
      {},
      onProgress,
    )
    if (result?.dubbed_url) {
      try {
        const { data } = await getDubbedStreamUrl(sourceVideo.value.video_id)
        dubbedDirectUrl.value = data.url
      } catch { dubbedDirectUrl.value = result.dubbed_url }
    }
    const updated = await videosStore.fetchVideo(sourceVideo.value.video_id)
    if (updated?.transcription) {
      transcription.value = updated.transcription
      translatedSegs.value = updated?.transcript_segments?.length
        ? updated.transcript_segments
        : _parseSegments(updated.transcription)
    }
    await _loadStreams()
    videoTab.value = 'dubbed'
    toast.success('Re-dub complete')
  } catch (e) {
    toast.error('Re-dub failed: ' + e.message)
  } finally {
    isProcessing.value = false
    currentJobType.value = null
    progressPct.value  = 0
    progressMsg.value  = ''
  }
}

async function fullReDub() {
  showRegenMenu.value = false
  generateDub()
}

// Displayed segments — prefer sourceVideo.transcript_segments, fall back to parsed
const displaySegments = computed(() => {
  if (sourceVideo.value?.transcript_segments?.length) {
    return sourceVideo.value.transcript_segments
  }
  return translatedSegs.value
})

// Download filename
const downloadFilename = computed(() => {
  const name = project.value?.metadata?.title ?? 'dubbed'
  return `${name.replace(/\s+/g, '_')}_dubbed.mp4`
})
</script>

<template>
  <div class="detail-view">

    <!-- Top bar -->
    <header class="detail-view__topbar">
      <div class="detail-view__topbar-left">
        <button
          class="detail-view__back-btn"
          data-testid="back-btn"
          title="Back to projects"
          @click="router.push({ name: 'projects' })"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Projects
        </button>
        <span class="detail-view__topbar-sep">/</span>
        <span class="detail-view__project-name">{{ project?.metadata?.title || 'Untitled project' }}</span>
        <div class="detail-view__meta-pills" v-if="sourceVideo">
          <span v-if="sourceVideo.detected_language" class="detail-view__meta-pill">
            {{ sourceVideo.detected_language.toUpperCase() }}
          </span>
          <span v-if="sourceVideo.duration_seconds" class="detail-view__meta-pill">
            {{ Math.round(sourceVideo.duration_seconds) }}s
          </span>
        </div>
      </div>

    </header>

    <!-- Workflow Stepper -->
    <div class="detail-view__stepper" data-testid="workflow-stepper">

      <!-- Step 1: Separate Audio -->
      <div
        class="detail-view__stepper-step"
        :class="`detail-view__stepper-step--${step1State}`"
        data-testid="step-1"
      >
        <div class="detail-view__step-circle">
          <span v-if="step1State === 'done'" class="detail-view__step-check">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <span v-else>1</span>
        </div>
        <span class="detail-view__step-label">Separate Audio</span>
        <button
          v-if="step1State === 'active'"
          class="btn btn-primary btn-sm detail-view__step-action"
          data-testid="separate-audio-btn"
          :disabled="isProcessing || !sourceVideo"
          @click="separateAudio"
        >
          <span v-if="isSeparating" class="detail-view__spinner"></span>
          {{ isSeparating ? progressMsg || 'Separating…' : 'Separate Audio' }}
        </button>
        <span v-if="step1State === 'active' && isSeparating" class="detail-view__step-pct">{{ progressPct }}%</span>
      </div>

      <span class="detail-view__step-arrow">→</span>

      <!-- Step 2: Transcribe -->
      <div
        class="detail-view__stepper-step"
        :class="`detail-view__stepper-step--${step2State}`"
        data-testid="step-2"
      >
        <div class="detail-view__step-circle">
          <span v-if="step2State === 'done'" class="detail-view__step-check">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <span v-else>2</span>
        </div>
        <span class="detail-view__step-label">Transcribe</span>
        <button
          v-if="step2State === 'active'"
          class="btn btn-primary btn-sm detail-view__step-action"
          data-testid="transcribe-btn"
          :disabled="isProcessing || !sourceVideo"
          @click="generateTranscription"
        >
          <span v-if="isTranscribing" class="detail-view__spinner"></span>
          {{ isTranscribing ? progressMsg || 'Transcribing…' : 'Transcribe' }}
        </button>
        <span v-if="step2State === 'active' && isTranscribing" class="detail-view__step-pct">{{ progressPct }}%</span>
      </div>

      <span class="detail-view__step-arrow">→</span>

      <!-- Step 3: Generate Dub -->
      <div
        class="detail-view__stepper-step"
        :class="`detail-view__stepper-step--${step3State}`"
        data-testid="step-3"
      >
        <div class="detail-view__step-circle">
          <span v-if="step3State === 'done'" class="detail-view__step-check">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <span v-else>3</span>
        </div>
        <span class="detail-view__step-label">Generate Dub</span>

        <!-- Active: show Generate Dub button -->
        <button
          v-if="step3State === 'active'"
          class="btn btn-primary btn-sm detail-view__step-action"
          data-testid="generate-dub-btn"
          :disabled="isProcessing || !sourceVideo"
          @click="generateDub"
        >
          <span v-if="isDubbing" class="detail-view__spinner"></span>
          {{ isDubbing ? progressMsg || 'Generating…' : 'Generate Dub' }}
        </button>
        <span v-if="step3State === 'active' && isDubbing" class="detail-view__step-pct">{{ progressPct }}%</span>

        <!-- Done: show Re-generate split button -->
        <div v-if="step3State === 'done'" class="detail-view__regen-wrap" @click.stop>
          <div class="detail-view__regen-split">
            <button
              class="btn btn-ghost btn-sm detail-view__regen-main"
              data-testid="regen-btn"
              :disabled="isProcessing"
              @click="showRegenMenu = !showRegenMenu"
            >
              Re-generate
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" class="detail-view__regen-caret">
                <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
          <div v-if="showRegenMenu" class="detail-view__regen-menu">
            <button class="detail-view__regen-item" @click="fullReDub">Full Re-dub</button>
            <button
              class="detail-view__regen-item"
              :disabled="!hasTranscription"
              @click="reDub"
            >
              Re-dub (skip transcription)
            </button>
          </div>
        </div>
      </div>

    </div>

    <!-- Body: two-pane layout -->
    <div class="detail-view__body">

      <!-- Left pane: Video Player (60%) -->
      <div class="detail-view__player-pane">

        <!-- Progress banner (when processing) -->
        <div v-if="isProcessing && (isDubbing || isTranscribing || isSeparating)" class="detail-view__progress-banner">
          <div class="detail-view__progress-spinner"></div>
          <div class="detail-view__progress-body">
            <span class="detail-view__progress-msg">{{ progressMsg || 'Processing…' }}</span>
            <div class="detail-view__progress-track">
              <div class="detail-view__progress-fill" :style="{ width: progressPct + '%' }"></div>
            </div>
          </div>
          <span class="detail-view__progress-pct">{{ progressPct }}%</span>
        </div>

        <!-- Original / Dubbed tab bar -->
        <div class="detail-view__tabs">
          <button
            class="detail-view__tab-btn"
            :class="{ active: videoTab === 'original' }"
            data-testid="tab-original"
            @click="videoTab = 'original'"
          >
            Original
          </button>
          <button
            class="detail-view__tab-btn"
            :class="{ active: videoTab === 'dubbed' }"
            data-testid="tab-dubbed"
            @click="videoTab = 'dubbed'"
          >
            Dubbed
            <span v-if="sortedVersions.length" class="detail-view__tab-count">{{ sortedVersions.length }}</span>
          </button>
        </div>

        <!-- Original tab content -->
        <template v-if="videoTab === 'original'">
          <div class="detail-view__video-container">
            <div v-if="videosStore.loading" class="detail-view__player-skeleton">
              <SkeletonBlock width="100%" height="100%" />
            </div>
            <template v-else-if="sourceVideo">
              <VideoPlayer :video-id="sourceVideo.video_id" />
            </template>
            <div v-else class="detail-view__player-empty">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.3">
                <rect x="2" y="2" width="20" height="20" rx="3"/>
                <polygon points="10 8 16 12 10 16 10 8" fill="currentColor" stroke="none"/>
              </svg>
              <p>No video in this project</p>
            </div>
          </div>
        </template>

        <!-- Dubbed tab content -->
        <template v-if="videoTab === 'dubbed'">
          <!-- Version selector if multiple versions -->
          <div v-if="sortedVersions.length > 1" class="detail-view__version-selector">
            <label class="detail-view__version-selector-label">Version</label>
            <select
              class="detail-view__version-select"
              :value="selectedVersionJobId ?? ''"
              @change="selectVersion($event.target.value || null)"
            >
              <option v-for="(v, i) in sortedVersions" :key="v.job_id" :value="i === 0 ? '' : v.job_id">
                {{ i === 0 ? 'Latest' : 'v' + (sortedVersions.length - i) }} · {{ fmtDate(v.created_at) }}
              </option>
            </select>
          </div>

          <div class="detail-view__video-container">
            <div v-if="isDubbing" class="detail-view__player-processing">
              <div class="detail-view__proc-spinner"></div>
              <span>{{ progressMsg || 'Generating dub…' }}</span>
              <span class="detail-view__proc-pct">{{ progressPct }}%</span>
              <div class="detail-view__proc-bar">
                <div class="detail-view__proc-fill" :style="{ width: progressPct + '%' }"></div>
              </div>
            </div>
            <template v-else-if="dubbedDirectUrl">
              <video :src="dubbedDirectUrl" controls class="detail-view__dubbed-video" />
            </template>
            <div v-else class="detail-view__player-empty" data-testid="no-dubbed-message">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.3">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              </svg>
              <p>No dubbed version yet</p>
              <p class="detail-view__player-hint">Complete step 3 to generate a dub</p>
            </div>
          </div>

          <!-- Download link -->
          <div v-if="dubbedDirectUrl" class="detail-view__download-bar">
            <a
              :href="dubbedDirectUrl"
              :download="downloadFilename"
              class="detail-view__download-link"
              data-testid="download-dubbed-link"
            >
              ↓ Download Dubbed MP4
            </a>
          </div>
        </template>

      </div>

      <!-- Right pane: Transcript + Versions (40%) -->
      <div class="detail-view__transcript-pane" data-testid="transcript-pane">

        <!-- Transcript header -->
        <div class="detail-view__pane-header">
          <span class="detail-view__pane-title">TRANSCRIPT</span>
          <span v-if="displaySegments.length" class="detail-view__pane-count">{{ displaySegments.length }}</span>
        </div>

        <!-- Segment list -->
        <div class="detail-view__transcript-list" v-if="displaySegments.length">
          <div
            v-for="(seg, i) in displaySegments"
            :key="i"
            class="detail-view__segment"
            :class="{ 'detail-view__segment--active': i === currentSegmentIndex }"
            data-testid="transcript-segment"
          >
            <span class="detail-view__segment-ts" data-testid="segment-timestamp">{{ fmtTimestamp(seg.start) }}</span>
            <span class="detail-view__segment-text" data-testid="segment-text">{{ seg.text }}</span>
          </div>
        </div>

        <!-- Empty transcript state -->
        <div v-else-if="isTranscribing" class="detail-view__transcript-loading">
          <SkeletonBlock width="100%" height="32px" />
          <SkeletonBlock width="80%" height="32px" />
          <SkeletonBlock width="90%" height="32px" />
        </div>
        <div v-else class="detail-view__transcript-empty">
          <p>No transcript yet.</p>
          <p class="detail-view__transcript-hint">
            {{ step1State !== 'done' ? 'Complete step 1 to separate audio first.' : 'Complete step 2 to generate a transcript.' }}
          </p>
        </div>

        <!-- Versions section -->
        <div v-if="sortedVersions.length" class="detail-view__versions" data-testid="versions-section">
          <div class="detail-view__pane-header detail-view__pane-header--border">
            <span class="detail-view__pane-title">VERSIONS</span>
            <span class="detail-view__pane-count">{{ sortedVersions.length }}</span>
          </div>
          <div class="detail-view__versions-list">
            <div
              v-for="(v, i) in sortedVersions"
              :key="v.job_id"
              class="detail-view__version-row"
              :class="{ 'detail-view__version-row--active': selectedVersionJobId === v.job_id || (i === 0 && !selectedVersionJobId) }"
            >
              <div
                class="detail-view__version-dot"
                :class="{ 'detail-view__version-dot--active': selectedVersionJobId === v.job_id || (i === 0 && !selectedVersionJobId) }"
              ></div>
              <div class="detail-view__version-info">
                <span class="detail-view__version-label">
                  <span v-if="i === 0" class="detail-view__version-badge">Latest</span>
                  <span v-else>v{{ sortedVersions.length - i }}</span>
                </span>
                <span class="detail-view__version-date">{{ fmtDate(v.created_at) }}</span>
              </div>
              <div class="detail-view__version-actions">
                <button
                  class="btn btn-ghost btn-xs"
                  :disabled="isProcessing || deletingVersionJobId === v.job_id"
                  @click="selectVersion(i === 0 ? null : v.job_id)"
                >
                  Load
                </button>
                <button
                  v-if="i > 0"
                  class="btn btn-ghost btn-xs detail-view__version-delete"
                  :disabled="isProcessing || deletingVersionJobId === v.job_id"
                  @click="deleteVersion(v.job_id)"
                >
                  <span v-if="deletingVersionJobId === v.job_id" class="detail-view__spinner detail-view__spinner--dark"></span>
                  <span v-else>Delete</span>
                </button>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

  </div>
</template>

<style scoped lang="scss">
@use '../assets/scss/views/ProjectDetailView';
</style>
