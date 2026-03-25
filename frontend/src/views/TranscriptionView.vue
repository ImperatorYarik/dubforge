<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useJobsStore } from '@/stores/jobs'
import { useToast } from '@/composables/useToast'
import * as videosApi from '@/api/videos'
import * as jobsApi from '@/api/jobs'

const router = useRouter()
const projectsStore = useProjectsStore()
const jobsStore = useJobsStore()
const toast = useToast()

// Upload state
const videoId = ref(null)
const fileName = ref('')
const fileSize = ref(0)
const uploadPct = ref(0)
const uploading = ref(false)
const isDragOver = ref(false)

// Options
const selectedModel = ref('large-v3')
const taskMode = ref('translate')   // 'translate' | 'transcribe'
const demucsEnabled = ref(true)
const language = ref('')

const MODELS = ['large-v3', 'large-v2', 'medium', 'small']

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

const TR_STEPS = ['Extract', 'Demucs', 'Whisper', 'Upload']
const TR_STEP_MAP = { extract: 0, transcribe: 0, demucs: 1, whisper: 2, upload: 3 }

// File handling
function onDragOver(e) { e.preventDefault(); isDragOver.value = true }
function onDragLeave() { isDragOver.value = false }
function onDrop(e) {
  e.preventDefault()
  isDragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleFile(file)
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
}

async function startJob() {
  const projectId = projectsStore.currentProjectId
  if (!projectId || !videoId.value) { toast.error('Upload a file first'); return }

  running.value = true
  taskId.value = null
  progressPct.value = 0
  progressStep.value = ''
  progressMsg.value = ''
  log.value = []
  activeStepIdx.value = 0
  doneSteps.value = new Set()
  result.value = null

  try {
    const options = {
      translate: taskMode.value === 'translate',
      model: selectedModel.value,
      skip_demucs: !demucsEnabled.value,
      language: language.value || null,
    }
    const { data } = await jobsApi.transcribeVideo(projectId, videoId.value, options)
    taskId.value = data.task_id
    jobsStore.startJob(data.task_id, 'transcribe', videoId.value, projectId)

    await jobsStore.connectWS(data.task_id, onProgress)
  } catch (e) {
    toast.error(e.message || 'Job failed')
  } finally {
    running.value = false
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
  const stepIdx = TR_STEP_MAP[d.step]
  if (stepIdx !== undefined && stepIdx > activeStepIdx.value) {
    for (let i = activeStepIdx.value; i < stepIdx; i++) doneSteps.value.add(i)
    activeStepIdx.value = stepIdx
  }
  if (d.pct >= 100) { doneSteps.value.add(activeStepIdx.value); activeStepIdx.value = -1 }
  const time = new Date().toTimeString().slice(0, 8)
  log.value.push(`${time} [${d.step}] ${d.message}`)
  if (log.value.length > 200) log.value.shift()
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
  dl('transcript.srt', lines, 'text/srt')
}

function exportJSON() {
  dl('transcript.json', JSON.stringify(result.value?.transcript_segments, null, 2), 'application/json')
}

function exportTXT() {
  const text = result.value?.transcript_segments?.map(s => s.text).join('\n') || result.value?.transcription || ''
  dl('transcript.txt', text, 'text/plain')
}

function dl(name, content, type) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([content], { type }))
  a.download = name
  a.click()
}

function goToDub() {
  router.push({ path: '/dub', state: { videoId: videoId.value, skipTranscription: true } })
}

function formatBytes(b) {
  if (!b) return ''
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <div class="view">
    <!-- Pipeline Steps -->
    <div class="steps-row">
      <div
        v-for="(step, i) in TR_STEPS"
        :key="i"
        class="step"
        :class="{ 'step-active': activeStepIdx === i, 'step-done': doneSteps.has(i) }"
      >
        <span v-if="doneSteps.has(i)" class="step-check">✓</span>
        {{ step }}
      </div>
    </div>

    <div class="workspace">
      <!-- Left col: Upload + Options -->
      <div class="left-col">
        <!-- Drop zone -->
        <div
          v-if="!videoId"
          class="dropzone"
          :class="{ dragover: isDragOver, uploading }"
          @dragover="onDragOver"
          @dragleave="onDragLeave"
          @drop="onDrop"
          @click="$refs.fileInput.click()"
        >
          <input ref="fileInput" type="file" accept="video/*,audio/*" style="display:none" @change="onFileInput" />
          <div v-if="uploading" class="dz-uploading">
            <div class="dz-progress-bar"><div class="dz-progress-fill" :style="{ width: uploadPct + '%' }"></div></div>
            <span class="dz-hint">Uploading {{ uploadPct }}%…</span>
          </div>
          <div v-else class="dz-idle">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>
            <p class="dz-title">Drop video or audio</p>
            <p class="dz-sub">MP4, MOV, MP3, WAV…</p>
          </div>
        </div>

        <div v-else class="file-chip">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/></svg>
          <span class="chip-fname">{{ fileName }}</span>
          <span v-if="fileSize" class="chip-size">{{ formatBytes(fileSize) }}</span>
          <button class="chip-remove" @click="removeFile">×</button>
        </div>

        <!-- Options -->
        <div class="options-panel">
          <div class="opt-row">
            <label class="opt-label">Model</label>
            <select class="input opt-select" v-model="selectedModel">
              <option v-for="m in MODELS" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>
          <div class="opt-row">
            <label class="opt-label">Task</label>
            <div class="mode-toggle">
              <button class="mode-btn" :class="{ active: taskMode === 'translate' }" @click="taskMode = 'translate'">Transcribe + Translate</button>
              <button class="mode-btn" :class="{ active: taskMode === 'transcribe' }" @click="taskMode = 'transcribe'">Transcribe Only</button>
            </div>
          </div>
          <div class="opt-row">
            <label class="opt-label">Demucs</label>
            <label class="toggle">
              <input type="checkbox" v-model="demucsEnabled" />
              <span class="toggle-track"></span>
            </label>
          </div>
          <div class="opt-row">
            <label class="opt-label">Language Hint</label>
            <select class="input opt-select" v-model="language">
              <option value="">Auto-detect</option>
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="it">Italian</option>
              <option value="pt">Portuguese</option>
              <option value="ru">Russian</option>
              <option value="ja">Japanese</option>
              <option value="zh">Chinese</option>
              <option value="ar">Arabic</option>
              <option value="ko">Korean</option>
            </select>
          </div>
        </div>

        <button
          class="btn btn-primary start-btn"
          :disabled="!videoId || running"
          @click="startJob"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          {{ running ? 'Processing…' : 'Start Transcription' }}
        </button>
      </div>

      <!-- Right col: Progress / Result -->
      <div class="right-col">
        <!-- Progress -->
        <div v-if="running || (taskId && !result)" class="progress-panel">
          <div class="prog-header">
            <span class="prog-step">{{ progressStep || 'initializing' }}</span>
            <span class="prog-pct">{{ progressPct }}%</span>
          </div>
          <div class="prog-track"><div class="prog-fill" :style="{ width: progressPct + '%' }"></div></div>
          <div class="prog-msg">{{ progressMsg }}</div>
          <div class="prog-log">
            <div v-for="(line, i) in log" :key="i" class="log-line">{{ line }}</div>
          </div>
        </div>

        <!-- Result -->
        <div v-if="result" class="result-block">
          <!-- Detection chips -->
          <div class="detect-chips">
            <span class="badge badge-ok" v-if="result.detected_language">
              <span class="badge-dot"></span>
              {{ result.detected_language?.toUpperCase() }}
            </span>
            <span class="badge badge-dim" v-if="result.segment_count">
              {{ result.segment_count }} segments
            </span>
            <span class="badge badge-dim" v-if="result.duration_seconds">
              {{ Math.floor(result.duration_seconds / 60) }}:{{ Math.floor(result.duration_seconds % 60).toString().padStart(2,'0') }}
            </span>
          </div>

          <!-- Segments -->
          <div class="transcript-panel">
            <div class="tp-header">
              <span class="section-label">TRANSCRIPT</span>
            </div>
            <div class="tp-segs">
              <div v-for="(seg, i) in result.transcript_segments" :key="i" class="tp-seg">
                <span class="seg-time">[{{ seg.start.toFixed(1) }}s – {{ seg.end.toFixed(1) }}s]</span>
                <span class="seg-text">{{ seg.text }}</span>
              </div>
              <div v-if="!result.transcript_segments?.length && result.transcription" class="tp-raw">
                {{ result.transcription }}
              </div>
            </div>
          </div>

          <!-- Export buttons -->
          <div class="result-actions">
            <button class="btn btn-ghost btn-sm" @click="exportSRT">Export SRT</button>
            <button class="btn btn-ghost btn-sm" @click="exportJSON">Export JSON</button>
            <button class="btn btn-ghost btn-sm" @click="exportTXT">Export TXT</button>
            <button class="btn btn-teal btn-sm" @click="goToDub">
              Use for Dubbing →
            </button>
          </div>
        </div>

        <div v-if="!running && !result && !taskId" class="idle-placeholder">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/></svg>
          <p>Upload a file and start transcription</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view { padding: 28px 32px; max-width: 1100px; display: flex; flex-direction: column; gap: 20px; }

.steps-row { display: flex; gap: 4px; }
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
.step-active { color: var(--amber); background: var(--amber-g); border-color: var(--b-amber); }
.step-done { color: var(--teal); background: var(--teal-g); border-color: var(--b-teal); }
.step-check { position: absolute; top: 2px; right: 4px; font-size: 8px; }

.workspace { display: grid; grid-template-columns: 320px 1fr; gap: 20px; align-items: start; }
.left-col, .right-col { min-width: 0; }

.dropzone {
  border: 1px dashed var(--border);
  border-radius: var(--radius-lg);
  padding: 28px 16px;
  text-align: center;
  cursor: pointer;
  background: var(--bg3);
  margin-bottom: 16px;
  transition: border-color 0.15s, background 0.15s;
}
.dropzone:hover, .dropzone.dragover { border-color: var(--b-amber); background: var(--amber-g); }
.dz-idle { display: flex; flex-direction: column; align-items: center; gap: 8px; color: var(--muted); }
.dz-title { font-size: 13px; font-weight: 500; color: var(--text); }
.dz-sub { font-size: 11px; }
.dz-uploading { display: flex; flex-direction: column; gap: 10px; align-items: center; }
.dz-progress-bar { width: 100%; height: 3px; background: var(--bg4); border-radius: 2px; overflow: hidden; }
.dz-progress-fill { height: 100%; background: var(--amber); transition: width 0.2s; }
.dz-hint { font-size: 12px; color: var(--muted); font-family: var(--font-mono); }

.file-chip { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: var(--bg3); border: 1px solid var(--b-amber); border-radius: var(--radius); margin-bottom: 16px; font-size: 12px; }
.chip-fname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip-size { font-family: var(--font-mono); font-size: 10px; color: var(--muted); }
.chip-remove { font-size: 16px; color: var(--muted); }
.chip-remove:hover { color: var(--red); }

.options-panel { display: flex; flex-direction: column; gap: 14px; padding: 16px; background: var(--bg3); border: 1px solid var(--border); border-radius: var(--radius-lg); margin-bottom: 16px; }
.opt-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.opt-label { font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); flex-shrink: 0; }
.opt-select { width: auto; min-width: 160px; background: var(--bg4); }

.mode-toggle { display: flex; gap: 4px; flex-wrap: wrap; }
.mode-btn { padding: 5px 8px; border-radius: var(--radius); font-size: 10px; font-family: var(--font-mono); background: var(--bg4); border: 1px solid var(--border); color: var(--muted); cursor: pointer; }
.mode-btn:hover { border-color: var(--b-amber); color: var(--text); }
.mode-btn.active { background: var(--amber-g); border-color: var(--b-amber); color: var(--amber); }

.toggle { position: relative; display: inline-block; width: 36px; height: 20px; cursor: pointer; }
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-track { position: absolute; inset: 0; border-radius: 10px; background: var(--bg4); border: 1px solid var(--border); transition: all 0.2s; }
.toggle-track::before { content: ''; position: absolute; width: 14px; height: 14px; left: 2px; top: 2px; border-radius: 50%; background: var(--muted); transition: all 0.2s; }
.toggle input:checked + .toggle-track { background: var(--amber-g); border-color: var(--b-amber); }
.toggle input:checked + .toggle-track::before { transform: translateX(16px); background: var(--amber); }

.start-btn { width: 100%; justify-content: center; padding: 12px; }

.progress-panel { background: var(--bg3); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px; display: flex; flex-direction: column; gap: 12px; }
.prog-header { display: flex; justify-content: space-between; align-items: center; }
.prog-step { font-family: var(--font-mono); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--amber); }
.prog-pct { font-family: var(--font-display); font-size: 20px; color: var(--amber); }
.prog-track { height: 3px; background: var(--bg4); border-radius: 2px; overflow: hidden; }
.prog-fill { height: 100%; background: var(--amber); transition: width 0.3s; }
.prog-msg { font-size: 12px; color: var(--muted); }
.prog-log { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 10px 12px; max-height: 200px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.log-line { font-family: var(--font-mono); font-size: 10px; color: var(--muted); white-space: pre-wrap; word-break: break-all; }

.result-block { display: flex; flex-direction: column; gap: 16px; }
.detect-chips { display: flex; gap: 8px; flex-wrap: wrap; }
.transcript-panel { background: var(--bg3); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; }
.tp-header { padding: 12px 16px; border-bottom: 1px solid var(--border); }
.tp-segs { max-height: 280px; overflow-y: auto; padding: 8px; }
.tp-seg { display: flex; gap: 10px; padding: 6px 8px; border-radius: var(--radius); font-size: 12px; }
.seg-time { font-family: var(--font-mono); font-size: 10px; color: var(--muted); white-space: nowrap; flex-shrink: 0; padding-top: 2px; }
.seg-text { color: var(--text); line-height: 1.4; }
.tp-raw { padding: 8px; font-size: 12px; color: var(--muted); white-space: pre-wrap; line-height: 1.6; }

.result-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.idle-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; min-height: 300px; color: var(--muted); font-size: 13px; text-align: center; }
</style>
