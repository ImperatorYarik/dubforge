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
import ContextReviewPanel from '@/components/ContextReviewPanel.vue'
import { getDubbedStreamUrl, getVocalsStreamUrl, getNoVocalsStreamUrl, getDubbedVersionStreamUrl, deleteDubbedVersion } from '@/api/videos'
import * as jobsApi from '@/api/jobs'
import * as llmApi from '@/api/llm'

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

// LLM translation mode state
const translationMethod   = ref('whisper')  // 'whisper' | 'llm'
const llmModel            = ref('')
const availableModels     = ref([])
const autoConfirmContext  = ref(false)
const collectedContext    = ref('')
const contextReviewModel  = ref('')
const contextRegenLoading = ref(false)
const llmProgressMsg      = ref('')

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

async function _fetchModels() {
  try {
    const { data } = await llmApi.getModels()
    availableModels.value = data.models || []
    if (availableModels.value.length && !llmModel.value) {
      llmModel.value = availableModels.value[0]
    }
  } catch {
    availableModels.value = []
  }
}

watch(translationMethod, (val) => {
  if (val === 'llm') _fetchModels()
})

async function _pollStatus(getStatus, intervalMs = 1500) {
  return new Promise((resolve, reject) => {
    const timer = setInterval(async () => {
      try {
        const { data } = await getStatus()
        if (data.status === 'completed') {
          clearInterval(timer)
          resolve(data)
        } else if (data.status === 'failed') {
          clearInterval(timer)
          reject(new Error(data.error || 'Task failed'))
        }
      } catch (e) {
        clearInterval(timer)
        reject(e)
      }
    }, intervalMs)
  })
}

async function generateDubWithLLM() {
  const video = sourceVideo.value
  if (!video) return

  isProcessing.value = true
  currentJobType.value = 'dub'
  progressPct.value = 0
  progressMsg.value = 'Starting…'
  dubbedDirectUrl.value = null
  translatedSegs.value = []
  selectedVersionJobId.value = null
  jobsStore.setLlmPhase(null)

  try {
    // Step 1: Transcribe (no translation)
    const { data: trData } = await jobsApi.transcribeVideo(route.params.id, video.video_id, {
      translate: false,
    })
    jobsStore.startJob(trData.task_id, 'transcribe', video.video_id, route.params.id)
    await jobsStore.connectWS(trData.task_id, onProgress)
    const trStatus = await jobsStore.fetchStatus(trData.task_id)
    const rawSegments = trStatus.result?.transcript_segments || []

    // Step 2: Collect context
    jobsStore.setLlmPhase('collecting_context')
    llmProgressMsg.value = 'Collecting context…'
    const model = llmModel.value || undefined
    const { data: ctxData } = await llmApi.collectContext(route.params.id, video.video_id, model)
    const ctxResult = await _pollStatus(() => llmApi.getContextStatus(ctxData.task_id))
    collectedContext.value = ctxResult.context
    contextReviewModel.value = ctxResult.model

    // Step 3: Review (or auto-confirm)
    if (!autoConfirmContext.value) {
      jobsStore.setLlmPhase('awaiting_review')
      // Suspend — ContextReviewPanel will call onContextConfirmed
      return
    }

    await _continueFromContext(rawSegments, collectedContext.value)
  } catch (e) {
    toast.error('LLM dubbing failed: ' + e.message)
    jobsStore.setLlmPhase(null)
  } finally {
    if (jobsStore.llmPhase !== 'awaiting_review') {
      isProcessing.value = false
      currentJobType.value = null
      progressPct.value = 0
      progressMsg.value = ''
      llmProgressMsg.value = ''
    }
  }
}

async function onContextConfirmed(editedContext) {
  collectedContext.value = editedContext
  jobsStore.setLlmPhase(null)

  const video = sourceVideo.value
  const rawSegments = video?.transcript_segments || []

  try {
    await _continueFromContext(rawSegments, editedContext)
  } catch (e) {
    toast.error('LLM dubbing failed: ' + e.message)
    jobsStore.setLlmPhase(null)
  } finally {
    isProcessing.value = false
    currentJobType.value = null
    progressPct.value = 0
    progressMsg.value = ''
    llmProgressMsg.value = ''
  }
}

async function onContextRegenerate() {
  contextRegenLoading.value = true
  try {
    const model = llmModel.value || undefined
    const { data: ctxData } = await llmApi.collectContext(route.params.id, sourceVideo.value.video_id, model)
    const ctxResult = await _pollStatus(() => llmApi.getContextStatus(ctxData.task_id))
    collectedContext.value = ctxResult.context
    contextReviewModel.value = ctxResult.model
  } catch (e) {
    toast.error('Context regeneration failed: ' + e.message)
  } finally {
    contextRegenLoading.value = false
  }
}

async function _continueFromContext(rawSegments, context) {
  const video = sourceVideo.value
  if (!video) return
  const model = llmModel.value || undefined

  // Step 4: Translate segments
  jobsStore.setLlmPhase('translating')
  llmProgressMsg.value = 'Translating segments…'
  progressPct.value = 0
  const { data: trSegData } = await llmApi.translateSegments({
    video_id: video.video_id,
    segments: rawSegments,
    context,
    model,
  })
  const trSegResult = await _pollStatus(() => llmApi.getTranslateStatus(trSegData.task_id))
  const translatedSegments = trSegResult.segments

  // Step 5: Dub with translated segments
  jobsStore.setLlmPhase('ready')
  progressMsg.value = 'Starting dub…'
  const result = await jobsStore.dub(
    route.params.id,
    video.video_id,
    { skip_transcription: true, segments: translatedSegments },
    onProgress,
  )

  if (result?.dubbed_url) {
    try {
      const { data } = await getDubbedStreamUrl(video.video_id)
      dubbedDirectUrl.value = data.url
    } catch { dubbedDirectUrl.value = result.dubbed_url }
  }
  const updated = await videosStore.fetchVideo(video.video_id)
  if (updated?.transcription) {
    transcription.value = updated.transcription
    translatedSegs.value = updated?.transcript_segments?.length
      ? updated.transcript_segments
      : _parseSegments(updated.transcription)
  }
  await _loadStreams()
  activeTab.value = 'versions'
  jobsStore.setLlmPhase(null)
  toast.success('LLM Dubbing complete')
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
  if (translationMethod.value === 'llm') {
    return generateDubWithLLM()
  }
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

      <div class="header-controls">
        <label class="translate-toggle" :class="{ active: translateMode }">
          <input type="checkbox" v-model="translateMode" :disabled="isProcessing" />
          Translate
        </label>
        <div class="translation-method-group">
          <span class="method-label">Translation:</span>
          <label class="method-radio" :class="{ active: translationMethod === 'whisper' }">
            <input type="radio" v-model="translationMethod" value="whisper" :disabled="isProcessing" />
            Whisper
          </label>
          <label class="method-radio" :class="{ active: translationMethod === 'llm' }">
            <input type="radio" v-model="translationMethod" value="llm" :disabled="isProcessing" />
            LLM (Ollama)
          </label>
        </div>
        <template v-if="translationMethod === 'llm'">
          <select
            v-model="llmModel"
            class="model-select"
            :disabled="isProcessing"
            data-testid="llm-model-select"
          >
            <option v-if="!availableModels.length" value="" disabled>Ollama unavailable</option>
            <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
          </select>
          <label class="auto-confirm-toggle">
            <input type="checkbox" v-model="autoConfirmContext" :disabled="isProcessing" />
            Auto-confirm context
          </label>
          <span class="llm-info-badge">ℹ LLM mode adds a context review step before translation</span>
        </template>
      </div>
    </header>

    <div class="content">

      <!-- ── Processing Banner ──────────────────────────────────── -->
      <div v-if="isProcessing && jobsStore.llmPhase !== 'awaiting_review'" class="progress-banner">
        <div class="banner-spinner"></div>
        <div class="banner-body">
          <span class="banner-msg">{{ llmProgressMsg || progressMsg || 'Processing…' }}</span>
          <div class="banner-track">
            <div class="banner-fill" :style="{ width: progressPct + '%' }"></div>
          </div>
        </div>
        <span class="banner-pct">{{ progressPct }}%</span>
      </div>

      <!-- ── LLM Context Review Panel ───────────────────────────── -->
      <ContextReviewPanel
        v-if="jobsStore.llmPhase === 'awaiting_review'"
        :context="collectedContext"
        :model="contextReviewModel"
        :loading="contextRegenLoading"
        @confirm="onContextConfirmed"
        @regenerate="onContextRegenerate"
      />

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

<style scoped lang="scss">
@use './ProjectDetailView';
</style>

