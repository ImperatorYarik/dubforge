<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useVideosStore } from '@/stores/videos'
import { useJobsStore } from '@/stores/jobs'
import { useToast } from '@/composables/useToast'
import VideoPlayer from '@/components/VideoPlayer.vue'
import TranscriptPanel from '@/components/TranscriptPanel.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'
import { getDubbedStreamUrl, getVocalsStreamUrl, getNoVocalsStreamUrl } from '@/api/videos'

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
const transcriptOpen  = ref(false)

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
  if (sourceVideo.value?.transcription) {
    transcription.value = sourceVideo.value.transcription
    translatedSegs.value = _parseSegments(sourceVideo.value.transcription)
  }
  await _loadStreams()
})

async function _loadStreams() {
  if (!sourceVideo.value) return
  if (sourceVideo.value?.dubbed_url) {
    try {
      const { data } = await getDubbedStreamUrl(sourceVideo.value.video_id)
      dubbedDirectUrl.value = data.url
    } catch { /* no dubbed video */ }
  }
  if (sourceVideo.value?.vocals_url) {
    try {
      const { data } = await getVocalsStreamUrl(sourceVideo.value.video_id)
      vocalsDirectUrl.value = data.url
    } catch {}
  }
  if (sourceVideo.value?.no_vocals_url) {
    try {
      const { data } = await getNoVocalsStreamUrl(sourceVideo.value.video_id)
      noVocalsDirectUrl.value = data.url
    } catch {}
  }
}

const project = computed(() => projectsStore.currentProject)
const sourceVideo = computed(() =>
  videosStore.videosForProject(route.params.id)[0] ?? null
)

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
    translatedSegs.value = _parseSegments(transcription.value)
    transcriptOpen.value = true
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
  try {
    const result = await jobsStore.dub(
      route.params.id,
      sourceVideo.value.video_id,
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
      translatedSegs.value = _parseSegments(updated.transcription)
      transcriptOpen.value = true
    }
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
  try {
    const result = await jobsStore.redub(
      route.params.id,
      sourceVideo.value.video_id,
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
      translatedSegs.value = _parseSegments(updated.transcription)
      transcriptOpen.value = true
    }
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

const isDubbing = computed(() => isProcessing.value && currentJobType.value === 'dub')
const isTranscribing = computed(() => isProcessing.value && currentJobType.value === 'transcribe')
const isSeparating = computed(() => isProcessing.value && currentJobType.value === 'separate')

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
</script>

<template>
  <div class="detail-page">

    <!-- ── Top Bar ─────────────────────────────────────────────── -->
    <header class="topbar">
      <div class="topbar-left">
        <button class="icon-btn" title="Back" @click="router.push({ name: 'projects' })">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <span class="topbar-title">{{ project?.metadata?.title || 'Untitled project' }}</span>
      </div>

      <div class="topbar-right">
        <label class="translate-toggle" :class="{ active: translateMode }">
          <input type="checkbox" v-model="translateMode" :disabled="isProcessing" />
          Translate
        </label>
        <button
          class="btn btn-ghost btn-sm"
          :disabled="isProcessing || !sourceVideo"
          @click="separateAudio"
        >
          <span v-if="isSeparating" class="spinner spinner-dark" />
          Separate Audio
        </button>
        <button
          class="btn btn-ghost btn-sm"
          :disabled="isProcessing || !sourceVideo"
          @click="generateTranscription"
        >
          <span v-if="isTranscribing" class="spinner spinner-dark" />
          Transcribe
        </button>
        <button
          class="btn btn-primary btn-sm"
          :disabled="isProcessing || !sourceVideo"
          @click="generateDub"
        >
          <span v-if="isDubbing" class="spinner" />
          Generate Dub
        </button>

        <div v-if="hasExtractedAudio" class="regen-wrap" @click.stop>
          <button
            class="btn btn-ghost btn-sm regen-btn"
            :disabled="isProcessing"
            :class="{ active: showRegenMenu }"
            title="Regenerate steps"
            @click="showRegenMenu = !showRegenMenu"
          >
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style="flex-shrink:0">
              <path d="M11 6.5A4.5 4.5 0 1 1 6.5 2H9M9 2l-2 2M9 2l-2-2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" style="flex-shrink:0">
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
      </div>
    </header>

    <div class="content">

      <!-- ── Processing banner ───────────────────────────────── -->
      <div v-if="isProcessing" class="progress-banner">
        <div class="banner-inner">
          <span class="banner-spinner"></span>
          <span class="banner-msg">{{ progressMsg || 'Processing…' }}</span>
          <div class="banner-bar">
            <div class="banner-fill" :style="{ width: progressPct + '%' }"></div>
          </div>
          <span class="banner-pct">{{ progressPct }}%</span>
        </div>
      </div>

      <!-- ── Videos grid ─────────────────────────────────────── -->
      <div class="videos-grid">

        <!-- Original video -->
        <div class="video-cell">
          <div class="cell-header">
            <span class="cell-label">Original</span>
            <span v-if="sourceVideo?.detected_language" class="cell-badge">
              {{ sourceVideo.detected_language.toUpperCase() }}
            </span>
            <span v-if="sourceVideo?.duration_seconds" class="cell-badge cell-badge-dim">
              {{ Math.round(sourceVideo.duration_seconds) }}s
            </span>
          </div>
          <div class="cell-player">
            <div v-if="videosStore.loading" class="player-skeleton">
              <SkeletonBlock width="100%" height="100%" />
            </div>
            <template v-else-if="sourceVideo">
              <VideoPlayer :video-id="sourceVideo.video_id" />
            </template>
            <div v-else class="player-empty">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.3"><rect x="2" y="2" width="20" height="20" rx="3"/><polygon points="10 8 16 12 10 16 10 8" fill="currentColor" stroke="none"/></svg>
              <p>No video in this project</p>
            </div>
          </div>
          <div v-if="sourceVideo" class="cell-status">
            <span :class="['status-pill', hasTranscription ? 'pill-ok' : 'pill-dim']">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2.5 2.5L8 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              {{ hasTranscription ? 'Transcribed' : 'No transcript' }}
            </span>
            <span v-if="hasExtractedAudio" class="status-pill pill-ok">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2.5 2.5L8 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              Separated
            </span>
          </div>
        </div>

        <!-- Dubbed video -->
        <div class="video-cell">
          <div class="cell-header">
            <span class="cell-label">Dubbed</span>
            <span v-if="dubbedDirectUrl" class="cell-badge cell-badge-ok">EN</span>
          </div>
          <div class="cell-player" :class="{ 'player-active': isDubbing }">
            <div v-if="isDubbing" class="player-processing">
              <div class="proc-spinner"></div>
              <p class="proc-msg">{{ progressMsg || 'Generating dub…' }}</p>
              <p class="proc-pct">{{ progressPct }}%</p>
              <div class="proc-bar"><div class="proc-fill" :style="{ width: progressPct + '%' }"></div></div>
            </div>
            <template v-else-if="dubbedDirectUrl">
              <video :src="dubbedDirectUrl" controls class="dubbed-video" />
            </template>
            <div v-else class="player-empty">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.3"><rect x="2" y="2" width="20" height="20" rx="3"/><path d="M8 12h8M8 8h5M8 16h6" stroke="currentColor" stroke-linecap="round"/></svg>
              <p>No dubbed video yet</p>
              <p class="empty-hint">Click <strong>Generate Dub</strong> to start</p>
            </div>
          </div>
          <div class="cell-status">
            <span :class="['status-pill', dubbedDirectUrl ? 'pill-ok' : 'pill-dim']">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2.5 2.5L8 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              {{ dubbedDirectUrl ? 'Dubbed' : 'Not dubbed' }}
            </span>
          </div>
        </div>
      </div>

      <!-- ── Separated audio tracks ──────────────────────────── -->
      <template v-if="vocalsDirectUrl || noVocalsDirectUrl || isSeparating">
        <div class="section-header">
          <span class="section-title">Separated Tracks</span>
        </div>
        <div class="audio-grid">
          <div class="audio-cell" v-if="vocalsDirectUrl || isSeparating">
            <div class="audio-cell-head">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>
              <span>Vocals</span>
            </div>
            <div v-if="isSeparating" class="audio-skeleton">
              <SkeletonBlock width="100%" height="40px" />
            </div>
            <audio v-else :src="vocalsDirectUrl" controls class="audio-el" />
          </div>
          <div class="audio-cell" v-if="noVocalsDirectUrl || isSeparating">
            <div class="audio-cell-head">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              <span>Background</span>
            </div>
            <div v-if="isSeparating" class="audio-skeleton">
              <SkeletonBlock width="100%" height="40px" />
            </div>
            <audio v-else :src="noVocalsDirectUrl" controls class="audio-el" />
          </div>
        </div>
      </template>

      <!-- ── Transcript ──────────────────────────────────────── -->
      <div class="section-header transcript-toggle" @click="transcriptOpen = !transcriptOpen">
        <span class="section-title">Transcript</span>
        <span v-if="hasTranscription" class="section-count">{{ translatedSegs.length || '' }}</span>
        <svg
          width="14" height="14" viewBox="0 0 14 14" fill="none"
          :style="{ transform: transcriptOpen ? 'rotate(180deg)' : '', transition: 'transform 0.2s' }"
        >
          <path d="M3 5l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>

      <div v-if="transcriptOpen" class="transcript-body">
        <template v-if="isTranscribing">
          <TranscriptPanel :segments="[]" :loading="true" />
        </template>
        <template v-else-if="translatedSegs.length">
          <TranscriptPanel :segments="translatedSegs" :editable="true" />
        </template>
        <div v-else-if="transcription" class="transcript-raw">
          <p v-for="(line, i) in transcription.split('\n').filter(l => l.trim())" :key="i">{{ line }}</p>
        </div>
        <div v-else class="transcript-empty">
          No transcript — click <strong>Transcribe</strong> to generate one.
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
  height: 48px;
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

.topbar-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

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
}
.icon-btn:hover { background: var(--bg3); color: var(--text); }

/* ── Translate toggle ── */
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
}
.translate-toggle.active { border-color: var(--b-amber); color: var(--amber); }
.translate-toggle input { accent-color: var(--amber); }

/* ── Content area ── */
.content {
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
  padding: 24px 28px 40px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* ── Progress banner ── */
.progress-banner {
  background: var(--amber-g);
  border: 1px solid var(--b-amber);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  margin-bottom: 20px;
}
.banner-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}
.banner-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,165,0,0.3);
  border-top-color: var(--amber);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}
.banner-msg {
  font-size: 12px;
  color: var(--amber);
  font-family: var(--font-mono);
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.banner-bar {
  width: 120px;
  height: 4px;
  background: rgba(255,165,0,0.2);
  border-radius: 2px;
  overflow: hidden;
  flex-shrink: 0;
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
  margin-bottom: 24px;
}

.video-cell {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cell-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 2px;
}

.cell-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  font-family: var(--font-mono);
}

.cell-badge {
  font-size: 10px;
  font-family: var(--font-mono);
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg3);
  border: 1px solid var(--border);
  color: var(--muted);
}
.cell-badge-ok {
  background: rgba(0,200,150,0.1);
  border-color: rgba(0,200,150,0.3);
  color: var(--teal);
}
.cell-badge-dim {
  color: var(--dim);
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

.player-skeleton {
  width: 100%;
  height: 100%;
}

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
.empty-hint {
  font-size: 11.5px;
  color: rgba(255,255,255,0.15);
}
.empty-hint strong { color: rgba(255,255,255,0.3); }

/* Processing overlay inside dubbed cell */
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
  border: 3px solid rgba(255,165,0,0.2);
  border-top-color: var(--amber);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.proc-msg { font-size: 13px; color: rgba(255,255,255,0.7); }
.proc-pct { font-size: 11px; font-family: var(--font-mono); color: var(--amber); }
.proc-bar {
  width: 160px;
  height: 3px;
  background: rgba(255,165,0,0.15);
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

.cell-status {
  display: flex;
  gap: 6px;
  padding: 0 2px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10.5px;
  font-family: var(--font-mono);
  padding: 3px 8px;
  border-radius: 20px;
  border: 1px solid var(--border);
  color: var(--dim);
  background: transparent;
}
.pill-ok {
  color: var(--teal);
  border-color: rgba(0,200,150,0.3);
  background: rgba(0,200,150,0.06);
}
.pill-dim {
  color: var(--dim);
}

/* ── Section headers ── */
.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 2px 10px;
  border-top: 1px solid var(--border);
  margin-top: 8px;
}
.section-header.transcript-toggle {
  cursor: pointer;
  user-select: none;
}
.section-header.transcript-toggle:hover .section-title { color: var(--text); }

.section-title {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  font-family: var(--font-mono);
  flex: 1;
}
.section-count {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--dim);
  background: var(--bg3);
  border: 1px solid var(--border);
  padding: 1px 6px;
  border-radius: 4px;
}

/* ── Audio tracks ── */
.audio-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 8px;
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

.audio-el {
  width: 100%;
  height: 40px;
}

.audio-skeleton {
  border-radius: var(--radius);
  overflow: hidden;
}

/* ── Transcript ── */
.transcript-body {
  padding: 0 0 24px;
}

.transcript-raw {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--text);
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  max-height: 300px;
  overflow-y: auto;
}
.transcript-raw p { margin: 0 0 4px; }

.transcript-empty {
  font-size: 12.5px;
  color: var(--muted);
  padding: 20px;
  text-align: center;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}
.transcript-empty strong { color: var(--text); }

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

/* ── Regen dropdown ── */
.regen-wrap { position: relative; }
.regen-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 0 8px;
}
.regen-btn.active { background: var(--bg3); border-color: var(--border); }
.regen-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 200px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 4px 16px rgba(0,0,0,0.2);
  z-index: 100;
  overflow: hidden;
}
.regen-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 9px 14px;
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

/* ── Responsive ── */
@media (max-width: 900px) {
  .videos-grid { grid-template-columns: 1fr; }
  .audio-grid { grid-template-columns: 1fr; }
}
</style>
