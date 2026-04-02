<script setup>
import { ref, computed, onMounted } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useJobsStore } from '@/stores/jobs'
import { useSystemStore } from '@/stores/system'
import { useToast } from '@/composables/useToast'
import * as videosApi from '@/api/videos'
import { deleteDubbedVersion, getDubbedVersionStreamUrl } from '@/api/videos'

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

// Project files (with presigned URLs)
const projectVideoResults = ref([])
const filesLoading = ref(false)

// Per-card version selection and deletion state (keyed by video_id)
const selectedVersionByVideo = ref({})   // { [video_id]: job_id | null }
const deletingVersionByVideo = ref({})   // { [video_id]: job_id | null }

function sortedVersionsFor(v) {
  return [...(v.dubbed_versions || [])].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
}

async function selectVersionForCard(v, jobId) {
  selectedVersionByVideo.value[v.video_id] = jobId || null
  // Update the card's dubbed_url to the presigned URL for the selected version
  const idx = projectVideoResults.value.findIndex(x => x.video_id === v.video_id)
  if (idx === -1) return
  try {
    if (jobId) {
      const { data } = await getDubbedVersionStreamUrl(v.video_id, jobId)
      projectVideoResults.value[idx] = { ...projectVideoResults.value[idx], dubbed_url: data.url }
    } else {
      // Reload latest
      const { data } = await videosApi.getDubbedStreamUrl(v.video_id)
      projectVideoResults.value[idx] = { ...projectVideoResults.value[idx], dubbed_url: data.url }
    }
  } catch {}
}

async function deleteVersionForCard(v, jobId) {
  deletingVersionByVideo.value[v.video_id] = jobId
  try {
    await deleteDubbedVersion(v.video_id, jobId)
    // Re-fetch this video's data
    const { data: updated } = await videosApi.getVideo(v.video_id)
    const presigned = {}
    await Promise.allSettled([
      videosApi.getStreamUrl(v.video_id).then(({ data }) => { presigned.original_url = data.url }).catch(() => {}),
      updated.dubbed_url ? videosApi.getDubbedStreamUrl(v.video_id).then(({ data }) => { presigned.dubbed_url = data.url }).catch(() => {}) : null,
      updated.vocals_url ? videosApi.getVocalsStreamUrl(v.video_id).then(({ data }) => { presigned.vocals_url = data.url }).catch(() => {}) : null,
      updated.no_vocals_url ? videosApi.getNoVocalsStreamUrl(v.video_id).then(({ data }) => { presigned.no_vocals_url = data.url }).catch(() => {}) : null,
    ].filter(Boolean))
    const idx = projectVideoResults.value.findIndex(x => x.video_id === v.video_id)
    if (idx !== -1) {
      projectVideoResults.value[idx] = { ...updated, ...presigned }
    }
    if (selectedVersionByVideo.value[v.video_id] === jobId) {
      delete selectedVersionByVideo.value[v.video_id]
    }
    toast.success('Version deleted')
  } catch (e) {
    toast.error('Delete failed: ' + e.message)
  } finally {
    deletingVersionByVideo.value[v.video_id] = null
  }
}

async function loadAllProjectFiles() {
  const pid = projectsStore.currentProjectId
  if (!pid) return
  filesLoading.value = true
  try {
    const { data } = await videosApi.listVideos()
    const videos = (data || []).filter(v => v.project_id === pid)
    const enriched = await Promise.all(videos.map(async v => {
      const urls = {}
      await Promise.allSettled([
        videosApi.getStreamUrl(v.video_id).then(({ data }) => { urls.original_url = data.url }).catch(() => {}),
        v.dubbed_url ? videosApi.getDubbedStreamUrl(v.video_id).then(({ data }) => { urls.dubbed_url = data.url }).catch(() => {}) : null,
        v.vocals_url ? videosApi.getVocalsStreamUrl(v.video_id).then(({ data }) => { urls.vocals_url = data.url }).catch(() => {}) : null,
        v.no_vocals_url ? videosApi.getNoVocalsStreamUrl(v.video_id).then(({ data }) => { urls.no_vocals_url = data.url }).catch(() => {}) : null,
      ].filter(Boolean))
      return { ...v, ...urls }
    }))
    projectVideoResults.value = enriched
  } catch {} finally {
    filesLoading.value = false
  }
}

function useForDubbing(video) {
  videoId.value = video.video_id
  fileName.value = `video (${new Date(video.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })})`
  fileSize.value = 0
  videoData.value = video
  loadResultFromVideo(video)
  window.scrollTo({ top: 0, behavior: 'smooth' })
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

async function tryRecoverActiveJob() {
  const pid = projectsStore.currentProjectId
  if (!pid) return

  const cutoff = Date.now() - 2 * 60 * 60 * 1000  // 2 hours
  const candidates = jobsStore.jobHistory.filter(
    j => j.projectId === pid && j.startedAt > cutoff
  )

  for (const job of candidates) {
    try {
      const status = await jobsStore.fetchStatus(job.taskId)
      if (!['PENDING', 'STARTED'].includes(status.state)) continue

      taskId.value = job.taskId
      videoId.value = job.videoId
      fileName.value = 'Recovering job…'
      running.value = true
      fetchVideoData(job.videoId).catch(() => {})

      jobsStore.connectWS(job.taskId, onProgress)
        .catch(() => {})
        .finally(async () => {
          running.value = false
          if (!taskId.value) return
          try {
            const s = await jobsStore.pollStatus(taskId.value)
            if (s.state === 'SUCCESS') {
              result.value = s.result
              if (videoId.value) {
                videosApi.getStreamUrl(videoId.value)
                  .then(({ data }) => { if (result.value) result.value = { ...result.value, original_url: data.url } })
                  .catch(() => {})
              }
            }
          } catch {}
          loadAllProjectFiles()
        })
      break
    } catch {}
  }
}

// Handle router state (from TranscriptionView "Use for Dubbing" button)
onMounted(async () => {
  const state = history.state
  if (state?.videoId) {
    videoId.value = state.videoId
    fileName.value = 'Pre-loaded video'
    fileSize.value = 0
    if (state.skipTranscription) mode.value = 'redub'
    fetchVideoData(state.videoId)
  }
  projectsStore.fetchProjects()
  loadAllProjectFiles()
  if (!videoId.value) await tryRecoverActiveJob()
})

async function loadResultFromVideo(video) {
  if (!video) return
  if (!video.dubbed_url && !video.transcription && !video.vocals_url) return

  const r = {
    video_id: video.video_id,
    transcript_segments: video.transcript_segments || [],
    transcription: video.transcription,
    detected_language: video.detected_language,
    duration_seconds: video.duration_seconds,
    segment_count: video.transcript_segments?.length,
  }

  await Promise.allSettled([
    video.video_url
      ? videosApi.getStreamUrl(video.video_id).then(({ data }) => { r.original_url = data.url }).catch(() => {})
      : Promise.resolve(),
    video.dubbed_url
      ? videosApi.getDubbedStreamUrl(video.video_id).then(({ data }) => { r.dubbed_url = data.url }).catch(() => {})
      : Promise.resolve(),
    video.vocals_url
      ? videosApi.getVocalsStreamUrl(video.video_id).then(({ data }) => { r.vocals_url = data.url }).catch(() => {})
      : Promise.resolve(),
    video.no_vocals_url
      ? videosApi.getNoVocalsStreamUrl(video.video_id).then(({ data }) => { r.no_vocals_url = data.url }).catch(() => {})
      : Promise.resolve(),
  ])

  result.value = r
}

async function fetchVideoData(id) {
  try {
    const { data } = await videosApi.getVideo(id)
    videoData.value = data
    await loadResultFromVideo(data)
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
        const status = await jobsStore.pollStatus(taskId.value)
        if (status.state === 'SUCCESS') {
          result.value = status.result
          // Enrich with original video presigned URL
          if (videoId.value) {
            videosApi.getStreamUrl(videoId.value)
              .then(({ data }) => { if (result.value) result.value = { ...result.value, original_url: data.url } })
              .catch(() => {})
          }
        } else if (status.error) {
          toast.error(status.error)
        }
      } catch {}
      loadAllProjectFiles()
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
  if (!videoId.value) return
  try {
    const { data: video } = await videosApi.getVideo(videoId.value)
    videoData.value = video
    await loadResultFromVideo(video)
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

    <!-- Pipeline Steps — only visible while a job is active -->
    <div v-if="running || (taskId && !result)" class="steps-row">
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

          <!-- Pick existing video -->
          <div v-if="projectVideoResults.length" class="picker-row">
            <span class="pick-hint">↓ Pick an existing video from Project Files below</span>
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
            <label class="opt-label" title="Lowers background music volume during speech segments so the dubbed voice is easier to hear">Audio Ducking</label>
            <label class="toggle">
              <input type="checkbox" v-model="duckingEnabled" />
              <span class="toggle-track"></span>
            </label>
          </div>

          <div class="opt-row">
            <label class="opt-label" title="Controls how much the TTS audio can be sped up or slowed down to match the original timing. A narrower range sounds more natural but may drift from timing.">Atempo Clamp</label>
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
          <!-- Videos row -->
          <div class="result-videos" :class="{ 'two-col': result.dubbed_url && result.original_url }">
            <div v-if="result.dubbed_url" class="result-video-wrap">
              <span class="result-video-label">DUBBED</span>
              <video
                ref="videoRef"
                class="result-video"
                :src="result.dubbed_url"
                controls
                @timeupdate="onTimeUpdate"
              ></video>
            </div>
            <div v-if="result.original_url" class="result-video-wrap">
              <span class="result-video-label">ORIGINAL</span>
              <video class="result-video" :src="result.original_url" controls></video>
            </div>
          </div>

          <!-- Audio tracks -->
          <div v-if="result.vocals_url || result.no_vocals_url" class="audio-tracks">
            <span class="section-label">SEPARATED TRACKS</span>
            <div class="tracks-grid">
              <div v-if="result.vocals_url" class="track-cell">
                <span class="track-label">Vocals</span>
                <audio :src="result.vocals_url" controls class="track-audio" />
              </div>
              <div v-if="result.no_vocals_url" class="track-cell">
                <span class="track-label">Background</span>
                <audio :src="result.no_vocals_url" controls class="track-audio" />
              </div>
            </div>
          </div>

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
            <a v-if="result.vocals_url" :href="result.vocals_url" download class="btn btn-ghost btn-sm">
              ↓ Vocals WAV
            </a>
            <a v-if="result.no_vocals_url" :href="result.no_vocals_url" download class="btn btn-ghost btn-sm">
              ↓ Background WAV
            </a>
            <button class="btn btn-ghost btn-sm" @click="refreshLinks">↻ Refresh links</button>
            <button class="btn btn-ghost btn-sm" @click="resetView">+ New Job</button>
          </div>
        </div>

        <!-- Idle placeholder -->
        <div v-if="!running && !result && !taskId" class="idle-placeholder">
          <div class="idle-steps">
            <div class="idle-step">
              <span class="idle-step-num">1</span>
              <div class="idle-step-text">
                <strong>Upload a video</strong>
                <span>Drag & drop or click to browse</span>
              </div>
            </div>
            <div class="idle-step-arrow">→</div>
            <div class="idle-step">
              <span class="idle-step-num">2</span>
              <div class="idle-step-text">
                <strong>Configure options</strong>
                <span>Choose mode & audio settings</span>
              </div>
            </div>
            <div class="idle-step-arrow">→</div>
            <div class="idle-step">
              <span class="idle-step-num">3</span>
              <div class="idle-step-text">
                <strong>Start Dubbing</strong>
                <span>AI transcribes & dubs to English</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Project Files -->
    <div v-if="projectsStore.currentProjectId" class="project-files">
      <div class="pf-header">
        <span class="section-label">PROJECT FILES</span>
        <button class="btn btn-ghost btn-sm" @click="loadAllProjectFiles">↻ Refresh</button>
      </div>

      <div v-if="filesLoading" class="pf-loading">Loading files…</div>
      <div v-else-if="!projectVideoResults.length" class="pf-empty">
        No videos yet — upload a video above to get started
      </div>

      <div v-for="v in projectVideoResults" :key="v.video_id" class="pf-card">
        <!-- Card header -->
        <div class="pf-card-header">
          <div class="pf-meta">
            <span class="pf-date">{{ new Date(v.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</span>
            <span v-if="v.detected_language" class="pf-badge pf-badge-dim">{{ v.detected_language.toUpperCase() }}</span>
            <span v-if="v.duration_seconds" class="pf-badge pf-badge-dim">{{ formatDuration(v.duration_seconds) }}</span>
            <span v-if="v.dubbed_url" class="pf-badge pf-badge-ok">DUBBED</span>
            <span v-if="v.transcript_segments?.length" class="pf-badge pf-badge-ok">TRANSCRIPT</span>
            <span v-if="v.vocals_url" class="pf-badge pf-badge-ok">SEPARATED</span>
          </div>
          <button class="btn btn-ghost btn-sm" @click="useForDubbing(v)">Use for dubbing →</button>
        </div>

        <!-- Video players -->
        <div class="pf-videos" :class="{ 'pf-two-col': v.dubbed_url && v.original_url }">
          <div v-if="v.original_url" class="pf-video-wrap">
            <span class="pf-video-label">ORIGINAL</span>
            <video :src="v.original_url" controls class="pf-video" preload="metadata" />
          </div>
          <div v-if="v.dubbed_url" class="pf-video-wrap">
            <div class="pf-dubbed-header">
              <span class="pf-video-label">DUBBED</span>
              <select
                v-if="sortedVersionsFor(v).length > 1"
                class="pf-version-select"
                :value="selectedVersionByVideo[v.video_id] ?? ''"
                @change="selectVersionForCard(v, $event.target.value || null)"
              >
                <option value="">Latest</option>
                <option
                  v-for="(ver, i) in sortedVersionsFor(v)"
                  :key="ver.job_id"
                  :value="ver.job_id"
                >v{{ sortedVersionsFor(v).length - i }} · {{ new Date(ver.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</option>
              </select>
            </div>
            <video :src="v.dubbed_url" controls class="pf-video" preload="metadata" />
            <!-- Delete old versions -->
            <div v-if="sortedVersionsFor(v).length > 1" class="pf-version-del-row">
              <span class="pf-del-label">Remove old:</span>
              <button
                v-for="(ver, i) in sortedVersionsFor(v).slice(1)"
                :key="ver.job_id"
                class="btn btn-ghost btn-xs pf-del-btn"
                :disabled="deletingVersionByVideo[v.video_id] === ver.job_id"
                @click="deleteVersionForCard(v, ver.job_id)"
              >
                <span v-if="deletingVersionByVideo[v.video_id] === ver.job_id" class="spinner spinner-dark" />
                v{{ sortedVersionsFor(v).length - 1 - i }} ✕
              </button>
            </div>
          </div>
        </div>

        <!-- Audio tracks -->
        <div v-if="v.vocals_url || v.no_vocals_url" class="pf-audio">
          <span class="section-label">SEPARATED TRACKS</span>
          <div class="pf-tracks">
            <div v-if="v.vocals_url" class="pf-track">
              <div class="pf-track-head">
                <span class="track-label">Vocals</span>
                <a :href="v.vocals_url" download class="btn btn-ghost btn-xs">↓ WAV</a>
              </div>
              <audio :src="v.vocals_url" controls class="track-audio" />
            </div>
            <div v-if="v.no_vocals_url" class="pf-track">
              <div class="pf-track-head">
                <span class="track-label">Background</span>
                <a :href="v.no_vocals_url" download class="btn btn-ghost btn-xs">↓ WAV</a>
              </div>
              <audio :src="v.no_vocals_url" controls class="track-audio" />
            </div>
          </div>
        </div>

        <!-- Downloads -->
        <div class="pf-actions">
          <a v-if="v.dubbed_url" :href="v.dubbed_url" download class="btn btn-teal btn-sm">↓ Dubbed MP4</a>
          <a v-if="v.original_url" :href="v.original_url" download class="btn btn-ghost btn-sm">↓ Original</a>
          <a v-if="v.vocals_url" :href="v.vocals_url" download class="btn btn-ghost btn-sm">↓ Vocals WAV</a>
          <a v-if="v.no_vocals_url" :href="v.no_vocals_url" download class="btn btn-ghost btn-sm">↓ Background WAV</a>
        </div>
      </div>
    </div>
  </div>
</template>


<style scoped lang="scss">
@use './DubbingView';
</style>
