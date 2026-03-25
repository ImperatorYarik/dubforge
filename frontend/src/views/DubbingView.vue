<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useJobsStore } from '@/stores/jobs'
import { useSystemStore } from '@/stores/system'
import { useToast } from '@/composables/useToast'
import * as videosApi from '@/api/videos'

const router = useRouter()
const route = useRoute()
const projectsStore = useProjectsStore()
const jobsStore = useJobsStore()
const systemStore = useSystemStore()
const toast = useToast()

// Upload state
const videoId = ref(null)
const fileName = ref('')
const fileSize = ref(0)
const uploadPct = ref(0)
const uploading = ref(false)
const isDragOver = ref(false)

// Job state
const taskId = ref(null)
const running = ref(false)
const progressPct = ref(0)
const progressStep = ref('')
const progressMsg = ref('')
const log = ref([])
const activeStepIdx = ref(-1)
const doneSteps = ref(new Set())

// Result state
const result = ref(null)
const videoRef = ref(null)
const activeSegmentIdx = ref(-1)

// Options
const mode = ref('full')       // 'full' | 'redub' | 'no-tts'
const duckingEnabled = ref(true)
const atempoMin = ref(0.75)

// Video data (for re-dub check)
const videoData = ref(null)

// Project video picker
const projectVideos = ref([])
const showPicker = ref(false)

async function loadProjectVideos() {
  try {
    const { data } = await videosApi.listVideos()
    const pid = projectsStore.currentProjectId
    projectVideos.value = (data || []).filter(v => v.project_id === pid)
  } catch {}
}

function pickVideo(video) {
  videoId.value = video.video_id
  fileName.value = `video (${new Date(video.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })})`
  fileSize.value = 0
  showPicker.value = false
  videoData.value = video
}

const canRedub = computed(() => videoData.value?.transcription || videoData.value?.transcript_segments?.length)

const STEPS = ['Download', 'Separate', 'Transcribe', 'Reference', 'Synthesize', 'Mix', 'Mux']

// Worker publishes step="video_dub" for all stages; derive step from pct ranges
function pctToStepIdx(pct) {
  if (pct < 10) return 0   // Download
  if (pct < 22) return 1   // Separate (Demucs)
  if (pct < 53) return 2   // Transcribe (Whisper)
  if (pct < 55) return 3   // Reference audio
  if (pct < 80) return 4   // Synthesize (TTS)
  if (pct < 90) return 5   // Mix
  return 6                 // Mux / Upload
}

// Stats
const stats = computed(() => {
  if (!result.value) return null
  return {
    duration: result.value.duration_seconds ? formatDuration(result.value.duration_seconds) : '—',
    segments: result.value.segment_count ?? result.value.transcript_segments?.length ?? '—',
    language: result.value.detected_language?.toUpperCase() ?? '—',
    status: 'DONE',
  }
})

// Handle router state (from TranscriptionView "Use for Dubbing" button)
onMounted(() => {
  const state = history.state
  if (state?.videoId) {
    videoId.value = state.videoId
    fileName.value = 'Pre-loaded video'
    fileSize.value = 0
    if (state.skipTranscription) mode.value = 'redub'
    fetchVideoData(state.videoId)
  }
  projectsStore.fetchProjects()
  loadProjectVideos()
})

async function fetchVideoData(id) {
  try {
    const { data } = await videosApi.getVideo(id)
    videoData.value = data
  } catch {}
}

// File drag & drop
function onDragOver(e) { e.preventDefault(); isDragOver.value = true }
function onDragLeave() { isDragOver.value = false }
function onDrop(e) {
  e.preventDefault()
  isDragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('video/')) handleFile(file)
}
function onFileInput(e) {
  const file = e.target.files?.[0]
  if (file) handleFile(file)
}

async function handleFile(file) {
  const projectId = projectsStore.currentProjectId
  if (!projectId) { toast.error('Select a project first'); return }
  uploading.value = true
  uploadPct.value = 0
  fileName.value = file.name
  fileSize.value = file.size
  try {
    const { data } = await videosApi.uploadVideo(file, projectId, (e) => {
      uploadPct.value = Math.round(e.loaded / e.total * 100)
    })
    videoId.value = data.video_id || data.upload_url?.split('/').pop()
    // Fetch video details after upload
    await fetchVideoData(videoId.value)
    toast.success('Video uploaded')
  } catch {
    toast.error('Upload failed')
    videoId.value = null
    fileName.value = ''
  } finally {
    uploading.value = false
  }
}

function removeFile() {
  videoId.value = null
  fileName.value = ''
  fileSize.value = 0
  videoData.value = null
}

async function startJob() {
  const projectId = projectsStore.currentProjectId
  if (!projectId || !videoId.value) { toast.error('Upload a video first'); return }

  running.value = true
  taskId.value = null
  progressPct.value = 0
  progressStep.value = ''
  progressMsg.value = ''
  log.value = []
  activeStepIdx.value = -1
  doneSteps.value = new Set()
  result.value = null

  try {
    const options = {
      ducking_enabled: duckingEnabled.value,
      ducking_level: duckingEnabled.value ? 0.1 : 1.0,
      atempo_min: atempoMin.value,
      atempo_max: 2.0 - atempoMin.value,
    }

    let submitRes
    if (mode.value === 'no-tts') {
      submitRes = await import('@/api/jobs').then(j => j.transcribeVideo(projectId, videoId.value))
    } else if (mode.value === 'redub') {
      submitRes = await import('@/api/jobs').then(j => j.dubVideo(projectId, videoId.value, { ...options, skip_transcription: true }))
    } else {
      submitRes = await import('@/api/jobs').then(j => j.dubVideo(projectId, videoId.value, options))
    }

    taskId.value = submitRes.data.task_id
    jobsStore.startJob(taskId.value, mode.value, videoId.value, projectId)

    await jobsStore.connectWS(taskId.value, onProgress)
  } catch (e) {
    toast.error(e.message || 'Job failed')
  } finally {
    running.value = false
    // Fetch final result
    if (taskId.value) {
      try {
        const status = await jobsStore.fetchStatus(taskId.value)
        if (status.state === 'SUCCESS') {
          result.value = status.result
        } else if (status.error) {
          toast.error(status.error)
        }
      } catch {}
    }
  }
}

function onProgress(d) {
  progressPct.value = d.pct ?? 0
  progressStep.value = d.step ?? ''
  progressMsg.value = d.message ?? ''

  const stepIdx = pctToStepIdx(d.pct ?? 0)
  if (stepIdx > activeStepIdx.value) {
    for (let i = activeStepIdx.value; i < stepIdx; i++) doneSteps.value.add(i)
    activeStepIdx.value = stepIdx
  }
  if (d.pct >= 100) {
    for (let i = 0; i <= activeStepIdx.value; i++) doneSteps.value.add(i)
    activeStepIdx.value = -1
  }

  const time = new Date().toTimeString().slice(0, 8)
  log.value.push(`${time} [${d.step}] ${d.message}`)
  if (log.value.length > 200) log.value.shift()
}

function onTimeUpdate() {
  if (!videoRef.value || !result.value?.transcript_segments?.length) return
  const t = videoRef.value.currentTime
  const segs = result.value.transcript_segments
  const idx = segs.findIndex((s, i) => {
    const next = segs[i + 1]
    return t >= s.start && (next ? t < next.start : true)
  })
  activeSegmentIdx.value = idx
}

function exportSRT() {
  const segs = result.value?.transcript_segments
  if (!segs?.length) return
  const lines = segs.map((s, i) => {
    const fmt = (t) => {
      const h = Math.floor(t / 3600).toString().padStart(2, '0')
      const m = Math.floor((t % 3600) / 60).toString().padStart(2, '0')
      const sec = Math.floor(t % 60).toString().padStart(2, '0')
      const ms = Math.round((t % 1) * 1000).toString().padStart(3, '0')
      return `${h}:${m}:${sec},${ms}`
    }
    return `${i + 1}\n${fmt(s.start)} --> ${fmt(s.end)}\n${s.text}\n`
  }).join('\n')
  download('transcript.srt', lines, 'text/srt')
}

function download(name, content, type) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([content], { type }))
  a.download = name
  a.click()
}

async function refreshLinks() {
  if (!taskId.value) return
  try {
    const status = await jobsStore.fetchStatus(taskId.value)
    if (status.result) result.value = status.result
    toast.success('Links refreshed')
  } catch { toast.error('Failed to refresh links') }
}

function resetView() {
  result.value = null
  taskId.value = null
  progressPct.value = 0
  log.value = []
  activeStepIdx.value = -1
  doneSteps.value = new Set()
}

function formatDuration(s) {
  const m = Math.floor(s / 60), sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

function formatBytes(b) {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <div class="view">
    <!-- Stats Row -->
    <div class="stats-row">
      <div class="stat-box">
        <span class="stat-label">Duration</span>
        <span class="stat-val">{{ stats?.duration ?? '—' }}</span>
      </div>
      <div class="stat-box">
        <span class="stat-label">Segments</span>
        <span class="stat-val">{{ stats?.segments ?? '—' }}</span>
      </div>
      <div class="stat-box">
        <span class="stat-label">Source Lang</span>
        <span class="stat-val">{{ stats?.language ?? '—' }}</span>
      </div>
      <div class="stat-box">
        <span class="stat-label">Status</span>
        <span class="stat-val" :class="stats?.status === 'DONE' ? 'val-teal' : ''">{{ stats?.status ?? '—' }}</span>
      </div>
    </div>

    <!-- Pipeline Steps -->
    <div class="steps-row">
      <div
        v-for="(step, i) in STEPS"
        :key="i"
        class="step"
        :class="{
          'step-active': activeStepIdx === i,
          'step-done': doneSteps.has(i),
        }"
      >
        <span v-if="doneSteps.has(i)" class="step-check">✓</span>
        {{ step }}
      </div>
    </div>

    <div class="workspace" :class="{ 'has-result': result }">
      <!-- Left: Upload + Options + Controls -->
      <div class="left-col">
        <!-- Upload Zone -->
        <div v-if="!videoId">
          <div
            class="dropzone"
            :class="{ dragover: isDragOver, uploading }"
            @dragover="onDragOver"
            @dragleave="onDragLeave"
            @drop="onDrop"
            @click="$refs.fileInput.click()"
          >
            <input ref="fileInput" type="file" accept="video/*" style="display:none" @change="onFileInput" />
            <div v-if="uploading" class="dz-uploading">
              <div class="dz-progress-bar">
                <div class="dz-progress-fill" :style="{ width: uploadPct + '%' }"></div>
              </div>
              <span class="dz-hint">Uploading {{ uploadPct }}%…</span>
            </div>
            <div v-else class="dz-idle">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>
              <p class="dz-title">Drop video here</p>
              <p class="dz-sub">or click to browse · MP4, MOV, MKV…</p>
            </div>
          </div>

          <!-- Pick from project -->
          <div v-if="projectVideos.length" class="picker-row">
            <button class="btn-pick" @click.stop="showPicker = !showPicker">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
              Pick from project ({{ projectVideos.length }})
            </button>
            <div v-if="showPicker" class="picker-list">
              <div
                v-for="v in projectVideos"
                :key="v.video_id"
                class="picker-item"
                @click="pickVideo(v)"
              >
                <span class="picker-name">{{ new Date(v.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</span>
                <span class="picker-badges">
                  <span v-if="v.transcription" class="badge-ok">TXT</span>
                  <span v-if="v.dubbed_url" class="badge-ok">DUB</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- File chip -->
        <div v-else class="file-chip">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span class="chip-fname">{{ fileName }}</span>
          <span v-if="fileSize" class="chip-size">{{ formatBytes(fileSize) }}</span>
          <button class="chip-remove" @click="removeFile" title="Remove">×</button>
        </div>

        <!-- Options -->
        <div class="options-panel">
          <div class="opt-row">
            <label class="opt-label">Target Language</label>
            <select class="input opt-select" disabled>
              <option>English (en)</option>
            </select>
          </div>

          <div class="opt-row">
            <label class="opt-label">Mode</label>
            <div class="mode-toggle">
              <button
                class="mode-btn"
                :class="{ active: mode === 'full' }"
                @click="mode = 'full'"
              >Full Dub</button>
              <button
                class="mode-btn"
                :class="{ active: mode === 'redub', disabled: !canRedub }"
                :disabled="!canRedub"
                :title="canRedub ? 'Reuses existing transcript' : 'No transcript found — run transcription first'"
                @click="canRedub && (mode = 'redub')"
              >Re-Dub</button>
              <button
                class="mode-btn"
                :class="{ active: mode === 'no-tts' }"
                @click="mode = 'no-tts'"
              >No TTS</button>
            </div>
          </div>

          <div class="opt-row">
            <label class="opt-label">Audio Ducking</label>
            <label class="toggle">
              <input type="checkbox" v-model="duckingEnabled" />
              <span class="toggle-track"></span>
            </label>
          </div>

          <div class="opt-row">
            <label class="opt-label">Atempo Clamp</label>
            <div class="slider-wrap">
              <input type="range" min="0.5" max="1.0" step="0.05" v-model.number="atempoMin" class="slider" />
              <span class="slider-val">{{ atempoMin }}× – {{ (2 - atempoMin).toFixed(2) }}×</span>
            </div>
          </div>
        </div>

        <!-- Worker busy warning -->
        <div v-if="systemStore.activeJobs > 0" class="worker-busy">
          <span>⏳</span> Worker busy · job will queue
        </div>

        <!-- Start Button -->
        <button
          class="btn btn-primary start-btn"
          :disabled="!videoId || running"
          @click="startJob"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          {{ running ? 'Processing…' : 'Start Dubbing' }}
        </button>
      </div>

      <!-- Right: Progress / Result -->
      <div class="right-col">
        <!-- Progress Panel -->
        <div v-if="running || (taskId && !result)" class="progress-panel">
          <div class="prog-header">
            <span class="prog-step">{{ progressStep || 'initializing' }}</span>
            <span class="prog-pct">{{ progressPct }}%</span>
          </div>
          <div class="prog-track">
            <div class="prog-fill" :style="{ width: progressPct + '%' }"></div>
          </div>
          <div class="prog-msg">{{ progressMsg }}</div>

          <!-- Log -->
          <div class="prog-log">
            <div v-for="(line, i) in log" :key="i" class="log-line">{{ line }}</div>
          </div>
        </div>

        <!-- Result Block -->
        <div v-if="result" class="result-block">
          <video
            ref="videoRef"
            class="result-video"
            :src="result.dubbed_url"
            controls
            @timeupdate="onTimeUpdate"
          ></video>

          <!-- Transcript -->
          <div v-if="result.transcript_segments?.length" class="transcript-panel">
            <div class="tp-header">
              <span class="section-label">TRANSCRIPT</span>
              <button class="btn btn-sm btn-ghost" @click="exportSRT">Export SRT</button>
            </div>
            <div class="tp-segs">
              <div
                v-for="(seg, i) in result.transcript_segments"
                :key="i"
                class="tp-seg"
                :class="{ active: activeSegmentIdx === i }"
                @click="videoRef && (videoRef.currentTime = seg.start)"
              >
                <span class="seg-time">[{{ seg.start.toFixed(1) }}s]</span>
                <span class="seg-text">{{ seg.text }}</span>
              </div>
            </div>
          </div>

          <!-- Action buttons -->
          <div class="result-actions">
            <a v-if="result.dubbed_url" :href="result.dubbed_url" download class="btn btn-teal btn-sm">
              ↓ Download MP4
            </a>
            <button class="btn btn-ghost btn-sm" @click="refreshLinks">↻ Refresh links</button>
            <button class="btn btn-ghost btn-sm" @click="resetView">+ New Job</button>
          </div>
        </div>

        <!-- Idle placeholder -->
        <div v-if="!running && !result && !taskId" class="idle-placeholder">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          <p>Upload a video and click Start Dubbing</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view {
  padding: 28px 32px;
  max-width: 1200px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Stats row */
.stats-row {
  display: flex;
  gap: 12px;
}
.stat-box {
  flex: 1;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat-label {
  font-family: var(--font-mono);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
}
.stat-val {
  font-family: var(--font-display);
  font-size: 22px;
  letter-spacing: 0.04em;
  color: var(--text);
}
.val-teal { color: var(--teal); }

/* Steps row */
.steps-row {
  display: flex;
  gap: 4px;
}
.step {
  flex: 1;
  text-align: center;
  padding: 8px 4px;
  border-radius: var(--radius);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--dim);
  background: var(--bg4);
  border: 1px solid var(--border);
  position: relative;
  transition: all 0.2s;
}
.step-active {
  color: var(--amber);
  background: var(--amber-g);
  border-color: var(--b-amber);
}
.step-done {
  color: var(--teal);
  background: var(--teal-g);
  border-color: var(--b-teal);
}
.step-check {
  position: absolute;
  top: 2px;
  right: 4px;
  font-size: 8px;
}

/* Workspace layout */
.workspace {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 20px;
  align-items: start;
}

/* Dropzone */
.dropzone {
  border: 1px dashed var(--border);
  border-radius: var(--radius-lg);
  padding: 32px 16px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  background: var(--bg3);
  margin-bottom: 16px;
}
.dropzone:hover, .dropzone.dragover {
  border-color: var(--b-amber);
  background: var(--amber-g);
}
.dz-idle { display: flex; flex-direction: column; align-items: center; gap: 8px; color: var(--muted); }
.dz-title { font-size: 13px; font-weight: 500; color: var(--text); }
.dz-sub { font-size: 11px; }

.dz-uploading { display: flex; flex-direction: column; gap: 10px; align-items: center; }
.dz-progress-bar { width: 100%; height: 3px; background: var(--bg4); border-radius: 2px; overflow: hidden; }
.dz-progress-fill { height: 100%; background: var(--amber); transition: width 0.2s; }
.dz-hint { font-size: 12px; color: var(--muted); font-family: var(--font-mono); }

/* File chip */
/* Picker */
.picker-row { margin-top: 6px; position: relative; }
.btn-pick {
  display: flex; align-items: center; gap: 6px;
  background: none; border: 1px solid var(--border);
  color: var(--muted); font-size: 11px; font-family: var(--font-mono);
  padding: 5px 10px; border-radius: 4px; cursor: pointer; width: 100%;
  transition: border-color 0.15s, color 0.15s;
}
.btn-pick:hover { border-color: var(--amber); color: var(--amber); }
.picker-list {
  position: absolute; top: calc(100% + 4px); left: 0; right: 0; z-index: 20;
  background: var(--bg3); border: 1px solid var(--border); border-radius: 6px;
  max-height: 200px; overflow-y: auto;
}
.picker-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; cursor: pointer; font-size: 11px; font-family: var(--font-mono);
  color: var(--muted); border-bottom: 1px solid var(--border);
  transition: background 0.1s, color 0.1s;
}
.picker-item:last-child { border-bottom: none; }
.picker-item:hover { background: var(--bg4); color: var(--text); }
.picker-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.picker-badges { display: flex; gap: 4px; flex-shrink: 0; margin-left: 8px; }
.badge-ok { background: var(--teal-g); color: var(--teal); border: 1px solid var(--teal); border-radius: 3px; padding: 1px 4px; font-size: 9px; }

.file-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg3);
  border: 1px solid var(--b-amber);
  border-radius: var(--radius);
  margin-bottom: 16px;
  color: var(--text);
  font-size: 12px;
}
.chip-fname { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip-size { font-family: var(--font-mono); font-size: 10px; color: var(--muted); flex-shrink: 0; }
.chip-remove { font-size: 16px; color: var(--muted); padding: 0 2px; flex-shrink: 0; }
.chip-remove:hover { color: var(--red); }

/* Options */
.options-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  margin-bottom: 16px;
}
.opt-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.opt-label {
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  flex-shrink: 0;
}
.opt-select { width: auto; min-width: 150px; background: var(--bg4); }

.mode-toggle { display: flex; gap: 4px; }
.mode-btn {
  padding: 5px 10px;
  border-radius: var(--radius);
  font-size: 11px;
  font-family: var(--font-mono);
  background: var(--bg4);
  border: 1px solid var(--border);
  color: var(--muted);
  cursor: pointer;
  transition: all 0.1s;
}
.mode-btn:hover:not(:disabled) { border-color: var(--b-amber); color: var(--text); }
.mode-btn.active { background: var(--amber-g); border-color: var(--b-amber); color: var(--amber); }
.mode-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* Toggle switch */
.toggle { position: relative; display: inline-block; width: 36px; height: 20px; cursor: pointer; }
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-track {
  position: absolute;
  inset: 0;
  border-radius: 10px;
  background: var(--bg4);
  border: 1px solid var(--border);
  transition: all 0.2s;
}
.toggle-track::before {
  content: '';
  position: absolute;
  width: 14px; height: 14px;
  left: 2px; top: 2px;
  border-radius: 50%;
  background: var(--muted);
  transition: all 0.2s;
}
.toggle input:checked + .toggle-track { background: var(--amber-g); border-color: var(--b-amber); }
.toggle input:checked + .toggle-track::before { transform: translateX(16px); background: var(--amber); }

/* Slider */
.slider-wrap { display: flex; align-items: center; gap: 10px; }
.slider { flex: 1; accent-color: var(--amber); }
.slider-val { font-family: var(--font-mono); font-size: 10px; color: var(--amber); flex-shrink: 0; min-width: 70px; }

.worker-busy {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--amber);
  padding: 6px 10px;
  background: var(--amber-g);
  border: 1px solid var(--b-amber);
  border-radius: var(--radius);
  margin-bottom: 12px;
}

.start-btn { width: 100%; justify-content: center; padding: 12px; font-size: 13px; }

/* Progress Panel */
.progress-panel {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.prog-header { display: flex; justify-content: space-between; align-items: center; }
.prog-step { font-family: var(--font-mono); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--amber); }
.prog-pct { font-family: var(--font-display); font-size: 20px; color: var(--amber); }
.prog-track { height: 3px; background: var(--bg4); border-radius: 2px; overflow: hidden; }
.prog-fill { height: 100%; background: var(--amber); transition: width 0.3s; }
.prog-msg { font-size: 12px; color: var(--muted); }

.prog-log {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 12px;
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.log-line {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted);
  white-space: pre-wrap;
  word-break: break-all;
}

/* Result */
.result-block { display: flex; flex-direction: column; gap: 16px; }
.result-video { width: 100%; border-radius: var(--radius-lg); background: #000; }

.transcript-panel {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.tp-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--border); }
.tp-segs { max-height: 200px; overflow-y: auto; padding: 8px; }
.tp-seg {
  display: flex;
  gap: 10px;
  padding: 6px 8px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background 0.1s;
  font-size: 12px;
}
.tp-seg:hover { background: var(--bg4); }
.tp-seg.active { background: var(--amber-g); }
.seg-time { font-family: var(--font-mono); font-size: 10px; color: var(--muted); white-space: nowrap; flex-shrink: 0; padding-top: 2px; }
.seg-text { color: var(--text); line-height: 1.4; }

.result-actions { display: flex; gap: 8px; flex-wrap: wrap; }

/* Idle */
.idle-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 300px;
  color: var(--muted);
  font-size: 13px;
  text-align: center;
}

/* Left col */
.left-col { min-width: 0; }
.right-col { min-width: 0; }
</style>
