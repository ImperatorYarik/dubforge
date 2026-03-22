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
import { getDubbedStreamUrl } from '@/api/videos'

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
const activeTab       = ref('original')  // 'original' | 'dubbed'
const panelOpen       = ref(true)

const transcription   = ref('')
const translateMode   = ref(false)
const panelWidth      = ref(280)
const showRegenMenu   = ref(false)
const currentJobType  = ref(null)  // 'dub' | 'transcribe' | null

const hasExtractedAudio = computed(() => !!sourceVideo.value?.vocals_url)
const hasTranscription  = computed(() => !!sourceVideo.value?.transcription || !!transcription.value)

function startResize(e) {
  e.preventDefault()
  const startX = e.clientX
  const startW = panelWidth.value
  function onMove(ev) {
    const delta = ev.clientX - startX
    panelWidth.value = Math.min(600, Math.max(160, startW + delta))
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

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
  }
  if (sourceVideo.value?.dubbed_url) {
    try {
      const { data } = await getDubbedStreamUrl(sourceVideo.value.video_id)
      dubbedDirectUrl.value = data.url
    } catch { /* no dubbed video */ }
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
      activeTab.value = 'dubbed'
    }
    const updated = await videosStore.fetchVideo(sourceVideo.value.video_id)
    if (updated?.transcription) {
      transcription.value = updated.transcription
      translatedSegs.value = updated.transcription.split('\n').filter(l => l.trim()).map(l => {
        const m = l.match(/\[(\d+\.\d+)s - (\d+\.\d+)s\] (.+)/)
        return m ? { start: parseFloat(m[1]), end: parseFloat(m[2]), text: m[3] } : null
      }).filter(Boolean)
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
      activeTab.value = 'dubbed'
    }
    const updated = await videosStore.fetchVideo(sourceVideo.value.video_id)
    if (updated?.transcription) {
      transcription.value = updated.transcription
      translatedSegs.value = updated.transcription.split('\n').filter(l => l.trim()).map(l => {
        const m = l.match(/\[(\d+\.\d+)s - (\d+\.\d+)s\] (.+)/)
        return m ? { start: parseFloat(m[1]), end: parseFloat(m[2]), text: m[3] } : null
      }).filter(Boolean)
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
</script>

<template>
  <div class="workspace">

    <!-- ── Top Bar ────────────────────────────────────────────── -->
    <header class="topbar">
      <div class="topbar-left">
        <button class="icon-btn" title="Back" @click="router.push({ name: 'projects' })">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <button class="icon-btn" :title="panelOpen ? 'Collapse panel' : 'Expand panel'" @click="panelOpen = !panelOpen">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="1.5" y="2.5" width="13" height="11" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
            <path d="M5.5 2.5v11" stroke="currentColor" stroke-width="1.4"/>
            <path v-if="panelOpen" d="M3 7l-1.5 1L3 9" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
            <path v-else d="M3.5 7l1.5 1-1.5 1" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>

      <div class="topbar-center">
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

        <!-- Regenerate dropdown — only visible when audio was already extracted -->
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

    <!-- ── Body ──────────────────────────────────────────────── -->
    <div class="body">

      <!-- Left panel: Files + Transcript -->
      <aside class="left-panel" :class="{ collapsed: !panelOpen }" :style="panelOpen ? { width: panelWidth + 'px' } : {}">
        <!-- Files section -->
        <div class="panel-section">
          <div class="panel-section-header">
            <span class="panel-section-title">Files</span>
          </div>

          <div class="panel-label">Videos</div>

          <div v-if="videosStore.loading" class="video-card-skeleton">
            <SkeletonBlock width="100%" height="90px" radius="var(--radius)" />
          </div>

          <div v-else-if="sourceVideo" class="video-card" :class="{ active: activeTab === 'original' }" @click="activeTab = 'original'">
            <div class="video-card-thumb">
              <img v-if="project?.metadata?.thumbnail" :src="project.metadata.thumbnail" alt="" class="thumb-img" />
              <div v-else class="thumb-fallback">▶</div>
            </div>
            <div class="video-card-info">
              <p class="video-card-name">{{ project?.metadata?.title || 'Source video' }}</p>
              <p class="video-card-meta">Original</p>
            </div>
          </div>

          <div v-if="dubbedDirectUrl" class="video-card" :class="{ active: activeTab === 'dubbed' }" @click="activeTab = 'dubbed'">
            <div class="video-card-thumb dubbed-thumb">
              <span>▶</span>
            </div>
            <div class="video-card-info">
              <p class="video-card-name">{{ project?.metadata?.title || 'Dubbed video' }}</p>
              <p class="video-card-meta">Dubbed</p>
            </div>
          </div>

          <div v-else-if="!sourceVideo && !videosStore.loading" class="panel-empty">
            No video found.
          </div>
        </div>

        <div class="panel-divider" />

        <!-- Transcript section -->
        <div class="panel-section panel-section-grow">
          <div class="panel-section-header">
            <span class="panel-section-title">Transcript</span>
          </div>

          <template v-if="isTranscribing">
            <TranscriptPanel :segments="[]" :loading="true" />
          </template>
          <div v-else-if="transcription" class="transcript-text">
            <p v-for="(line, i) in transcription.split('\n').filter(l => l.trim())" :key="i">{{ line }}</p>
          </div>
          <div v-else class="panel-empty">
            No transcript yet — click <strong>Transcribe</strong>.
          </div>
        </div>
      </aside>

      <!-- Divider / resize handle -->
      <div class="panel-resize-handle" v-show="panelOpen" @mousedown="startResize" />

      <!-- Main: video + controls -->
      <main class="main">

        <!-- Video player -->
        <div class="player-area">

          <!-- Processing overlay -->
          <div v-if="isDubbing" class="processing-overlay">
            <div class="processing-inner">
              <div class="processing-spinner" />
              <p class="processing-msg">{{ progressMsg || 'Processing…' }}</p>
              <p class="processing-pct">{{ progressPct }}%</p>
              <div class="processing-bar">
                <div class="processing-fill" :style="{ width: progressPct + '%' }" />
              </div>
            </div>
          </div>

          <!-- Original video -->
          <template v-if="activeTab === 'original'">
            <div v-if="sourceVideo" class="player-wrap">
              <VideoPlayer :video-id="sourceVideo.video_id" />
            </div>
            <div v-else class="player-empty">
              <p>No video in this project.</p>
            </div>
          </template>

          <!-- Dubbed video -->
          <template v-else-if="activeTab === 'dubbed'">
            <div v-if="dubbedDirectUrl" class="player-wrap">
              <video
                :src="dubbedDirectUrl"
                controls
                class="dubbed-video"
              />
            </div>
            <div v-else class="player-empty">
              <p>No dubbed video yet.</p>
              <p class="player-hint">Click <strong>Generate Dub</strong> to start.</p>
            </div>
          </template>
        </div>

        <!-- Tab bar -->
        <div class="tab-bar">
          <button class="tab-btn" :class="{ active: activeTab === 'original' }" @click="activeTab = 'original'">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="1" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.4"/>
              <path d="M5 4.5l4 2.5-4 2.5V4.5z" fill="currentColor"/>
            </svg>
            Original
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'dubbed', disabled: !dubbedDirectUrl }"
            :disabled="!dubbedDirectUrl"
            @click="dubbedDirectUrl && (activeTab = 'dubbed')"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="1" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.4"/>
              <path d="M4 4.5h6M4 7h4M4 9.5h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
            </svg>
            Dubbed
          </button>
        </div>

        <!-- Translated segments / timeline -->
        <div v-if="translatedSegs.length || (isDubbing)" class="timeline-panel">
          <div class="timeline-header">
            <span class="panel-label" style="margin-bottom:0">Translated Script</span>
          </div>
          <div class="timeline-scroll">
            <TranscriptPanel
              :segments="translatedSegs"
              :loading="isDubbing"
              :editable="true"
            />
          </div>
        </div>

      </main>
    </div>

  </div>
</template>

<style scoped>
/* ── Layout shell ── */
.workspace {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: var(--surface);
}

/* ── Top bar ── */
.topbar {
  display: flex;
  align-items: center;
  height: 48px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
  gap: 12px;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 80px;
}

.topbar-center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.topbar-title {
  font-size: 13.5px;
  font-weight: 500;
  letter-spacing: -0.015em;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 400px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 80px;
  justify-content: flex-end;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 6px;
  color: var(--text-muted);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}
.icon-btn:hover { background: var(--surface-subtle); color: var(--text); }

/* ── Translate toggle ── */
.translate-toggle {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
  padding: 4px 10px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--surface);
  transition: border-color 0.15s, color 0.15s;
}
.translate-toggle.active { border-color: var(--text); color: var(--text); }
.translate-toggle input { accent-color: var(--accent); }

/* ── Body ── */
.body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── Left panel ── */
.left-panel {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  overflow: hidden;
  background: var(--surface);
  transition: opacity 0.18s ease;
}
.left-panel.collapsed {
  width: 0;
  opacity: 0;
  border-right: none;
}

.panel-section {
  padding: 16px 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}
.panel-section-grow {
  flex: 1;
  overflow: hidden;
  padding-bottom: 0;
}

.panel-section-header {
  margin-bottom: 4px;
}
.panel-section-title {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: -0.015em;
  color: var(--text);
}

.panel-label {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.panel-divider {
  height: 1px;
  background: var(--border);
  flex-shrink: 0;
}

.panel-empty {
  font-size: 12.5px;
  color: var(--text-placeholder);
  padding: 12px 0 4px;
}

/* ── Video cards in left panel ── */
.video-card {
  display: flex;
  gap: 10px;
  padding: 8px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background 0.1s;
  border: 1px solid transparent;
}
.video-card:hover { background: var(--surface-subtle); }
.video-card.active {
  background: var(--surface-subtle);
  border-color: var(--border);
}

.video-card-thumb {
  width: 72px;
  height: 48px;
  border-radius: 4px;
  overflow: hidden;
  background: #111;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.thumb-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumb-fallback { font-size: 16px; color: rgba(255,255,255,0.4); }
.dubbed-thumb { background: #1a1a1a; }

.video-card-info { min-width: 0; }
.video-card-name {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.video-card-meta {
  font-size: 11.5px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* ── Transcript in left panel ── */
.transcript-text {
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text);
  overflow-y: auto;
  flex: 1;
  padding-right: 4px;
}
.transcript-text p { margin: 0 0 5px; }

/* ── Resize handle ── */
.panel-resize-handle {
  width: 5px;
  background: var(--border);
  flex-shrink: 0;
  cursor: col-resize;
  transition: background 0.15s;
  position: relative;
  z-index: 10;
}
.panel-resize-handle:hover,
.panel-resize-handle:active {
  background: var(--accent, #4f8ef7);
}

/* ── Main content ── */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: auto;
  background: var(--surface);
}

/* ── Player area ── */
.player-area {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  width: 100%;
  max-width: 1280px;
  height: 720px;
  flex-shrink: 0;
  align-self: center;
}

.player-wrap {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dubbed-video {
  max-width: 100%;
  max-height: 100%;
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  background: #000;
}

.player-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: rgba(255,255,255,0.3);
  font-size: 13px;
  text-align: center;
}
.player-hint { font-size: 12px; color: rgba(255,255,255,0.2); }

/* ── Processing overlay ── */
.processing-overlay {
  position: absolute;
  inset: 0;
  background: rgba(10,10,10,0.88);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}
.processing-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  color: rgba(255,255,255,0.85);
  text-align: center;
}
.processing-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(255,255,255,0.12);
  border-top-color: rgba(255,255,255,0.85);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.processing-msg { font-size: 14px; font-weight: 500; letter-spacing: -0.01em; }
.processing-pct { font-size: 12px; color: rgba(255,255,255,0.45); }
.processing-bar {
  width: 180px;
  height: 3px;
  background: rgba(255,255,255,0.12);
  border-radius: 2px;
  overflow: hidden;
}
.processing-fill {
  height: 100%;
  background: rgba(255,255,255,0.7);
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* ── Tab bar ── */
.tab-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px 16px;
  background: var(--surface);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.1s, color 0.1s, border-color 0.1s;
  letter-spacing: -0.01em;
}
.tab-btn:hover:not(:disabled) { background: var(--surface-subtle); color: var(--text); }
.tab-btn.active {
  background: var(--surface-subtle);
  color: var(--text);
  border-color: var(--border);
}
.tab-btn:disabled { opacity: 0.35; cursor: default; }

/* ── Timeline/transcript panel ── */
.timeline-panel {
  background: var(--surface);
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  max-height: 220px;
  flex-shrink: 0;
}
.timeline-header {
  padding: 10px 16px 6px;
  flex-shrink: 0;
}
.timeline-scroll {
  overflow-y: auto;
  padding: 0 8px 8px;
  flex: 1;
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

/* ── Regenerate dropdown ── */
.regen-wrap {
  position: relative;
}
.regen-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 0 8px;
}
.regen-btn.active {
  background: var(--surface-subtle);
  border-color: var(--border);
}
.regen-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 200px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
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
.regen-item:hover:not(:disabled) { background: var(--surface-subtle); }
.regen-item:disabled { opacity: 0.4; cursor: default; }

/* ── VideoPlayer override: fill player-area ── */
.player-wrap :deep(.video-wrap) {
  width: 100%;
  height: 100%;
  border-radius: 0;
  background: #000;
}
.player-wrap :deep(.player) {
  width: 100%;
  height: 100%;
  max-height: 100%;
  object-fit: contain;
}
</style>
