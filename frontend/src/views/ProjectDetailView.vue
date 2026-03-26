<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useVideosStore } from '@/stores/videos'
import { useJobsStore } from '@/stores/jobs'
import { useToast } from '@/composables/useToast'
import VideoPlayer from '@/components/VideoPlayer.vue'
import TranscriptPanel from '@/components/TranscriptPanel.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import { getDubbedStreamUrl, getVocalsStreamUrl, getNoVocalsStreamUrl, getDubbedVersionStreamUrl, deleteDubbedVersion } from '@/api/videos'

const route  = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()
const videosStore   = useVideosStore()
const jobsStore     = useJobsStore()
const toast = useToast()

const dubbedDirectUrl  = ref(null)
const vocalsDirectUrl  = ref(null)
const noVocalsDirectUrl = ref(null)
const translatedSegs   = ref([])
const isProcessing     = ref(false)
const progressPct      = ref(0)
const progressMsg      = ref('')

const transcription   = ref('')
const translateMode   = ref(false)
const showRegenMenu   = ref(false)
const currentJobType  = ref(null)  // 'dub' | 'transcribe' | 'separate' | null

// Tab navigation
const activeTab = ref('transcript') // 'transcript' | 'audio' | 'versions'

// Version management
const selectedVersionJobId = ref(null)   // null = latest
const deletingVersionJobId = ref(null)

const dubbedVersions = computed(() => sourceVideo.value?.dubbed_versions ?? [])
const sortedVersions = computed(() =>
  [...dubbedVersions.value].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
)

const hasExtractedAudio = computed(() => !!sourceVideo.value?.vocals_url)
const hasTranscription  = computed(() => !!sourceVideo.value?.transcription || !!transcription.value)

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
  // Auto-select best tab
  if (hasTranscription.value) activeTab.value = 'transcript'
  else if (hasExtractedAudio.value) activeTab.value = 'audio'
  else if (sortedVersions.value.length > 1) activeTab.value = 'versions'
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

const project = computed(() =>
  projectsStore.projects.find(p => p.project_id === route.params.id) ?? null
)
const sourceVideo = computed(() =>
  videosStore.videosForProject(route.params.id)[0] ?? null
)

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
      translateMode.value,
      onProgress,
    )
    const updated = await videosStore.fetchVideo(sourceVideo.value.video_id)
    transcription.value = updated?.transcription ?? ''
    translatedSegs.value = updated?.transcript_segments?.length
      ? updated.transcript_segments
      : _parseSegments(transcription.value)
    activeTab.value = 'transcript'
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
    activeTab.value = 'versions'
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
    activeTab.value = 'versions'
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

function reTranscribe() {
  showRegenMenu.value = false
  generateTranscription()
}

const isDubbing      = computed(() => isProcessing.value && currentJobType.value === 'dub')
const isTranscribing = computed(() => isProcessing.value && currentJobType.value === 'transcribe')
const isSeparating   = computed(() => isProcessing.value && currentJobType.value === 'separate')

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
    activeTab.value = 'audio'
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

function fmtDate(d) {
  return new Date(d).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="detail-page">

    <!-- ── Top Bar ──────────────────────────────────────────────── -->
    <header class="topbar">
      <div class="topbar-left">
        <button class="icon-btn" title="Back" @click="router.push({ name: 'projects' })">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <div class="topbar-title-group">
          <span class="topbar-title">{{ project?.metadata?.title || 'Untitled project' }}</span>
          <div class="topbar-meta" v-if="sourceVideo">
            <span v-if="sourceVideo.detected_language" class="meta-badge">{{ sourceVideo.detected_language.toUpperCase() }}</span>
            <span v-if="sourceVideo.duration_seconds" class="meta-badge meta-badge-dim">{{ Math.round(sourceVideo.duration_seconds) }}s</span>
            <span v-if="hasTranscription" class="meta-badge meta-badge-ok">Transcribed</span>
            <span v-if="hasExtractedAudio" class="meta-badge meta-badge-ok">Separated</span>
            <span v-if="dubbedDirectUrl" class="meta-badge meta-badge-ok">Dubbed</span>
          </div>
        </div>
      </div>

      <label class="translate-toggle" :class="{ active: translateMode }">
        <input type="checkbox" v-model="translateMode" :disabled="isProcessing" />
        Translate
      </label>
    </header>

    <div class="content">

      <!-- ── Processing Banner ──────────────────────────────────── -->
      <div v-if="isProcessing" class="progress-banner">
        <div class="banner-spinner"></div>
        <div class="banner-body">
          <span class="banner-msg">{{ progressMsg || 'Processing…' }}</span>
          <div class="banner-track">
            <div class="banner-fill" :style="{ width: progressPct + '%' }"></div>
          </div>
        </div>
        <span class="banner-pct">{{ progressPct }}%</span>
      </div>

      <!-- ── Video Comparison ───────────────────────────────────── -->
      <div class="videos-grid">

        <!-- Original -->
        <div class="video-cell">
          <div class="cell-label">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="3"/><polygon points="10 8 16 12 10 16 10 8" fill="currentColor" stroke="none"/></svg>
            Original
          </div>
          <div class="cell-player">
            <div v-if="videosStore.loading" class="player-skeleton"><SkeletonBlock width="100%" height="100%" /></div>
            <template v-else-if="sourceVideo">
              <VideoPlayer :video-id="sourceVideo.video_id" />
            </template>
            <div v-else class="player-empty">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.3"><rect x="2" y="2" width="20" height="20" rx="3"/><polygon points="10 8 16 12 10 16 10 8" fill="currentColor" stroke="none"/></svg>
              <p>No video in this project</p>
            </div>
          </div>
        </div>

        <!-- Dubbed -->
        <div class="video-cell">
          <div class="cell-label">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>
            Dubbed
            <span v-if="sortedVersions.length > 0" class="cell-version-tag">
              {{ selectedVersionJobId ? 'v' + (sortedVersions.length - sortedVersions.findIndex(v => v.job_id === selectedVersionJobId)) : 'Latest' }}
            </span>
          </div>
          <div class="cell-player" :class="{ 'player-active': isDubbing }">
            <div v-if="isDubbing" class="player-processing">
              <div class="proc-spinner"></div>
              <span class="proc-msg">{{ progressMsg || 'Generating dub…' }}</span>
              <span class="proc-pct">{{ progressPct }}%</span>
              <div class="proc-bar"><div class="proc-fill" :style="{ width: progressPct + '%' }"></div></div>
            </div>
            <template v-else-if="dubbedDirectUrl">
              <video :src="dubbedDirectUrl" controls class="dubbed-video" />
            </template>
            <div v-else class="player-empty">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.3"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>
              <p>No dubbed video yet</p>
              <p class="empty-hint">Click <strong>Generate Dub</strong> below</p>
            </div>
          </div>
        </div>

      </div>

      <!-- ── Action Toolbar ─────────────────────────────────────── -->
      <div class="action-bar">
        <div class="action-bar-left">
          <button
            class="btn btn-ghost btn-sm"
            :disabled="isProcessing || !sourceVideo"
            @click="separateAudio"
          >
            <span v-if="isSeparating" class="spinner spinner-dark" />
            <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>
            Separate Audio
          </button>
          <button
            class="btn btn-ghost btn-sm"
            :disabled="isProcessing || !sourceVideo"
            @click="generateTranscription"
          >
            <span v-if="isTranscribing" class="spinner spinner-dark" />
            <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
            Transcribe
          </button>
        </div>
        <div class="action-bar-right">
          <div v-if="hasExtractedAudio" class="regen-wrap" @click.stop>
            <button
              class="btn btn-ghost btn-sm regen-btn"
              :disabled="isProcessing"
              :class="{ active: showRegenMenu }"
              @click="showRegenMenu = !showRegenMenu"
            >
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <path d="M11 6.5A4.5 4.5 0 1 1 6.5 2H9M9 2l-2 2M9 2l-2-2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Regenerate
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
            <div v-if="showRegenMenu" class="regen-menu">
              <button class="regen-item" @click="reTranscribe">
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M11 6.5A4.5 4.5 0 1 1 6.5 2H9M9 2l-2 2M9 2l-2-2" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"/></svg>
                Re-transcribe
              </button>
              <button class="regen-item" :disabled="!hasTranscription" @click="reDub">
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M11 6.5A4.5 4.5 0 1 1 6.5 2H9M9 2l-2 2M9 2l-2-2" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"/></svg>
                Re-dub (keep transcript)
              </button>
            </div>
          </div>
          <button
            class="btn btn-primary btn-sm"
            :disabled="isProcessing || !sourceVideo"
            @click="generateDub"
          >
            <span v-if="isDubbing" class="spinner" />
            <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Generate Dub
          </button>
        </div>
      </div>

      <!-- ── Tabs ───────────────────────────────────────────────── -->
      <div class="tabs-bar">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'transcript' }"
          @click="activeTab = 'transcript'"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          Transcript
          <span v-if="translatedSegs.length" class="tab-count">{{ translatedSegs.length }}</span>
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'audio' }"
          @click="activeTab = 'audio'"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
          Audio Tracks
          <span v-if="hasExtractedAudio" class="tab-dot tab-dot-ok"></span>
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'versions' }"
          @click="activeTab = 'versions'"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>
          Versions
          <span v-if="sortedVersions.length" class="tab-count">{{ sortedVersions.length }}</span>
        </button>
      </div>

      <!-- ── Tab: Transcript ────────────────────────────────────── -->
      <div v-if="activeTab === 'transcript'" class="tab-panel">
        <template v-if="isTranscribing">
          <TranscriptPanel :segments="[]" :loading="true" />
        </template>
        <template v-else-if="translatedSegs.length">
          <TranscriptPanel :segments="translatedSegs" :editable="true" />
        </template>
        <div v-else-if="transcription" class="transcript-raw">
          <p v-for="(line, i) in transcription.split('\n').filter(l => l.trim())" :key="i">{{ line }}</p>
        </div>
        <div v-else class="tab-empty">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <p>No transcript yet.</p>
          <p class="tab-empty-hint">Click <strong>Transcribe</strong> to generate one.</p>
        </div>
      </div>

      <!-- ── Tab: Audio Tracks ──────────────────────────────────── -->
      <div v-if="activeTab === 'audio'" class="tab-panel">
        <template v-if="vocalsDirectUrl || noVocalsDirectUrl || isSeparating">
          <div class="audio-grid">
            <div class="audio-cell" v-if="vocalsDirectUrl || isSeparating">
              <div class="audio-cell-head">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>
                <span>Vocals</span>
              </div>
              <div v-if="isSeparating" class="audio-skeleton"><SkeletonBlock width="100%" height="40px" /></div>
              <audio v-else :src="vocalsDirectUrl" controls class="audio-el" />
            </div>
            <div class="audio-cell" v-if="noVocalsDirectUrl || isSeparating">
              <div class="audio-cell-head">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
                <span>Background</span>
              </div>
              <div v-if="isSeparating" class="audio-skeleton"><SkeletonBlock width="100%" height="40px" /></div>
              <audio v-else :src="noVocalsDirectUrl" controls class="audio-el" />
            </div>
          </div>
        </template>
        <div v-else class="tab-empty">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>
          <p>No audio tracks yet.</p>
          <p class="tab-empty-hint">Click <strong>Separate Audio</strong> to extract vocals and background.</p>
        </div>
      </div>

      <!-- ── Tab: Versions ──────────────────────────────────────── -->
      <div v-if="activeTab === 'versions'" class="tab-panel">
        <template v-if="sortedVersions.length">
          <div class="versions-list">
            <div
              v-for="(v, i) in sortedVersions"
              :key="v.job_id"
              class="version-row"
              :class="{ 'version-row-active': selectedVersionJobId === v.job_id || (i === 0 && !selectedVersionJobId) }"
            >
              <div class="version-radio">
                <div class="version-dot" :class="{ 'dot-active': selectedVersionJobId === v.job_id || (i === 0 && !selectedVersionJobId) }"></div>
              </div>
              <div class="version-info">
                <span class="version-label">
                  v{{ sortedVersions.length - i }}
                  <span v-if="i === 0" class="version-latest-badge">Latest</span>
                </span>
                <span class="version-date">{{ fmtDate(v.created_at) }}</span>
              </div>
              <div class="version-actions">
                <button
                  class="btn btn-ghost btn-xs version-load-btn"
                  :class="{ 'btn-active': selectedVersionJobId === v.job_id || (i === 0 && !selectedVersionJobId) }"
                  :disabled="isProcessing || deletingVersionJobId === v.job_id"
                  @click="selectVersion(i === 0 ? null : v.job_id)"
                >
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                  Load
                </button>
                <button
                  v-if="i > 0"
                  class="btn btn-ghost btn-xs version-del-btn"
                  :disabled="isProcessing || deletingVersionJobId === v.job_id"
                  @click="deleteVersion(v.job_id)"
                >
                  <span v-if="deletingVersionJobId === v.job_id" class="spinner spinner-dark" />
                  <svg v-else width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                  Delete
                </button>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="tab-empty">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <p>No dubbed versions yet.</p>
          <p class="tab-empty-hint">Click <strong>Generate Dub</strong> to create the first one.</p>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
/* ── Page layout ── */
.detail-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg);
}

/* ── Top bar ── */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
  padding: 0 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg2);
  flex-shrink: 0;
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 20;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.topbar-title-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.topbar-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1;
}

.topbar-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: nowrap;
}

.meta-badge {
  font-size: 9.5px;
  font-family: var(--font-mono);
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--bg3);
  border: 1px solid var(--border);
  color: var(--muted);
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.meta-badge-ok {
  background: rgba(24,197,160,0.08);
  border-color: rgba(24,197,160,0.2);
  color: var(--teal);
}
.meta-badge-dim { color: var(--dim); }

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 6px;
  color: var(--muted);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
  flex-shrink: 0;
}
.icon-btn:hover { background: var(--bg3); color: var(--text); }

.translate-toggle {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
  user-select: none;
  padding: 4px 10px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: transparent;
  transition: border-color 0.15s, color 0.15s;
  flex-shrink: 0;
}
.translate-toggle.active { border-color: var(--b-amber); color: var(--amber); }
.translate-toggle input { accent-color: var(--amber); }

/* ── Content ── */
.content {
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
  padding: 24px 28px 48px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* ── Progress Banner ── */
.progress-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--amber-g);
  border: 1px solid var(--b-amber);
  border-radius: var(--radius-lg);
  padding: 10px 16px;
  margin-bottom: 20px;
}
.banner-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(232,160,32,0.2);
  border-top-color: var(--amber);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}
.banner-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.banner-msg {
  font-size: 12px;
  color: var(--amber);
  font-family: var(--font-mono);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.banner-track {
  height: 3px;
  background: rgba(232,160,32,0.15);
  border-radius: 2px;
  overflow: hidden;
}
.banner-fill {
  height: 100%;
  background: var(--amber);
  border-radius: 2px;
  transition: width 0.3s;
}
.banner-pct {
  font-size: 11px;
  color: var(--amber);
  font-family: var(--font-mono);
  min-width: 28px;
  text-align: right;
  flex-shrink: 0;
}

/* ── Videos grid ── */
.videos-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 0;
}

.video-cell {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cell-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  font-family: var(--font-mono);
  padding: 0 2px;
}

.cell-version-tag {
  margin-left: auto;
  font-size: 9.5px;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(232,160,32,0.12);
  border: 1px solid var(--b-amber);
  color: var(--amber);
  letter-spacing: 0.04em;
}

.cell-player {
  background: #0a0a0a;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border);
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.cell-player.player-active {
  border-color: var(--b-amber);
}

.player-skeleton { width: 100%; height: 100%; }

.player-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: rgba(255,255,255,0.25);
  font-size: 12.5px;
  text-align: center;
  padding: 24px;
}
.empty-hint { font-size: 11.5px; color: rgba(255,255,255,0.15); }
.empty-hint strong { color: rgba(255,255,255,0.3); }

.player-processing {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  color: rgba(255,255,255,0.8);
  text-align: center;
  width: 100%;
}
.proc-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(232,160,32,0.2);
  border-top-color: var(--amber);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.proc-msg { font-size: 13px; color: rgba(255,255,255,0.7); }
.proc-pct { font-size: 11px; font-family: var(--font-mono); color: var(--amber); }
.proc-bar {
  width: 160px;
  height: 3px;
  background: rgba(232,160,32,0.15);
  border-radius: 2px;
  overflow: hidden;
}
.proc-fill {
  height: 100%;
  background: var(--amber);
  border-radius: 2px;
  transition: width 0.3s;
}

.dubbed-video {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  background: #000;
}

/* ── Action Toolbar ── */
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 0;
  margin-top: 4px;
  border-bottom: 1px solid var(--border);
}
.action-bar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.action-bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── Regen dropdown ── */
.regen-wrap { position: relative; }
.regen-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.regen-btn.active { background: var(--bg3); border-color: rgba(255,255,255,0.1); }
.regen-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 210px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  z-index: 100;
  overflow: hidden;
}
.regen-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  font-size: 12.5px;
  color: var(--text);
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background 0.1s;
}
.regen-item:hover:not(:disabled) { background: var(--bg3); }
.regen-item:disabled { opacity: 0.4; cursor: default; }

/* ── Tabs ── */
.tabs-bar {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 14px 0 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 12px;
  font-family: var(--font-mono);
  font-weight: 500;
  letter-spacing: 0.03em;
  color: var(--muted);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
  border-radius: var(--radius) var(--radius) 0 0;
}
.tab-btn:hover { color: var(--text); background: var(--bg3); }
.tab-btn.active {
  color: var(--text);
  border-bottom-color: var(--amber);
}

.tab-count {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 10px;
  background: var(--bg4);
  border: 1px solid var(--border);
  color: var(--dim);
  font-family: var(--font-mono);
}
.tab-btn.active .tab-count {
  background: rgba(232,160,32,0.1);
  border-color: var(--b-amber);
  color: var(--amber);
}

.tab-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--dim);
}
.tab-dot-ok { background: var(--teal); }

/* ── Tab panels ── */
.tab-panel {
  padding: 20px 0 0;
}

.tab-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 48px 24px;
  color: rgba(255,255,255,0.25);
  font-size: 13px;
  text-align: center;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}
.tab-empty-hint { font-size: 12px; color: rgba(255,255,255,0.15); }
.tab-empty-hint strong { color: rgba(255,255,255,0.3); }

/* ── Transcript ── */
.transcript-raw {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--text);
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  max-height: 320px;
  overflow-y: auto;
}
.transcript-raw p { margin: 0 0 4px; }

/* ── Audio grid ── */
.audio-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.audio-cell {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.audio-cell-head {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--text);
  font-weight: 500;
}
.audio-el { width: 100%; height: 40px; }
.audio-skeleton { border-radius: var(--radius); overflow: hidden; }

/* ── Versions list ── */
.versions-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.version-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  transition: border-color 0.15s, background 0.15s;
}
.version-row-active {
  border-color: var(--b-amber);
  background: rgba(232,160,32,0.04);
}

.version-radio { flex-shrink: 0; }
.version-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid var(--dim);
  background: transparent;
  transition: border-color 0.15s, background 0.15s;
}
.dot-active {
  border-color: var(--amber);
  background: var(--amber);
}

.version-info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}
.version-label {
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 6px;
}
.version-latest-badge {
  font-size: 9.5px;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(24,197,160,0.1);
  border: 1px solid rgba(24,197,160,0.2);
  color: var(--teal);
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.version-date {
  font-size: 11.5px;
  color: var(--muted);
  font-family: var(--font-mono);
}

.version-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.version-load-btn {
  font-size: 11px;
  padding: 4px 10px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.version-load-btn.btn-active {
  color: var(--amber);
  border-color: var(--b-amber);
  background: rgba(232,160,32,0.06);
}

.version-del-btn {
  font-size: 11px;
  padding: 4px 10px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--dim);
}
.version-del-btn:hover:not(:disabled) {
  color: var(--red);
  border-color: var(--b-red);
  background: var(--red-g);
}

/* ── VideoPlayer fill ── */
.cell-player :deep(.video-wrap) {
  width: 100%;
  height: 100%;
  border-radius: 0;
  background: #000;
}
.cell-player :deep(.player) {
  width: 100%;
  height: 100%;
  max-height: 100%;
  object-fit: contain;
}

/* ── Spinners ── */
.spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: rgba(255,255,255,0.9);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  flex-shrink: 0;
}
.spinner-dark {
  border: 2px solid rgba(0,0,0,0.15);
  border-top-color: rgba(0,0,0,0.7);
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Responsive ── */
@media (max-width: 900px) {
  .videos-grid { grid-template-columns: 1fr; }
  .audio-grid { grid-template-columns: 1fr; }
  .action-bar { flex-direction: column; align-items: stretch; }
  .action-bar-left, .action-bar-right { width: 100%; justify-content: stretch; }
  .tabs-bar { overflow-x: auto; }
}
</style>
