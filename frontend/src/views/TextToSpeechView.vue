<script setup>
import { ref, computed, onMounted } from 'vue'
import * as ttsApi from '@/api/tts'
import { getProgressWsUrl } from '@/api/jobs'
import { useToast } from '@/composables/useToast'
import SkeletonBlock from '@/components/SkeletonBlock.vue'

const toast = useToast()
const voices = ref([])
const selectedVoice = ref('')
const selectedFormat = ref('wav')
const text = ref('')
const searchQuery = ref('')
const isGenerating = ref(false)
const loadingVoices = ref(true)
const progressPct = ref(0)
const progressMsg = ref('')
const audioUrl = ref(null)
const audioFormat = ref('wav')
const audioEl = ref(null)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)

const MAX_CHARS = 2000
const charWarn = computed(() => text.value.length > 1800)

const filteredVoices = computed(() => {
  const q = searchQuery.value.toLowerCase()
  if (!q) return voices.value
  return voices.value.filter(v => v.name.toLowerCase().includes(q))
})

onMounted(async () => {
  try {
    const { data } = await ttsApi.getVoices()
    voices.value = data
    if (data.length) selectedVoice.value = data[0].name
  } catch {
    toast.error('Failed to load voices')
  } finally {
    loadingVoices.value = false
  }
})

function selectVoice(name) {
  selectedVoice.value = name
}

function voiceInitials(name) {
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

function voiceColor(name) {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) & 0xffffffff
  const hue = Math.abs(hash) % 360
  return `hsl(${hue}, 50%, 30%)`
}

async function generate() {
  if (!text.value.trim() || !selectedVoice.value) return
  isGenerating.value = true
  audioUrl.value = null
  progressPct.value = 0
  progressMsg.value = 'Submitting…'

  try {
    const { data } = await ttsApi.generateTts(text.value, selectedVoice.value, selectedFormat.value)
    // Poll status since TTS pipeline doesn't publish progress via WebSocket
    const result = await pollStatus(data.task_id)
    if (result?.audio_url) {
      audioUrl.value = result.audio_url
      audioFormat.value = result.format || selectedFormat.value
    }
  } catch (e) {
    toast.error(e.message || 'Generation failed')
  } finally {
    isGenerating.value = false
  }
}

async function pollStatus(taskId) {
  const maxAttempts = 60
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise(r => setTimeout(r, 1500))
    progressPct.value = Math.min(90, (i / maxAttempts) * 90)
    progressMsg.value = `Synthesizing… (${i * 1.5}s)`
    const { data } = await ttsApi.getTtsStatus(taskId)
    if (data.status === 'completed') {
      progressPct.value = 100
      return data.result
    }
    if (data.status === 'failed') {
      throw new Error(data.error || 'TTS generation failed')
    }
  }
  throw new Error('Timed out waiting for TTS result')
}

function togglePlay() {
  if (!audioEl.value) return
  if (isPlaying.value) {
    audioEl.value.pause()
  } else {
    audioEl.value.play()
  }
}

function onTimeUpdate() {
  if (!audioEl.value) return
  currentTime.value = audioEl.value.currentTime
  duration.value = audioEl.value.duration || 0
}

function onLoadedMetadata() {
  if (!audioEl.value) return
  duration.value = audioEl.value.duration
}

function onEnded() { isPlaying.value = false }

function scrub(e) {
  if (!audioEl.value || !duration.value) return
  const rect = e.currentTarget.getBoundingClientRect()
  const ratio = (e.clientX - rect.left) / rect.width
  audioEl.value.currentTime = ratio * duration.value
}

function formatTime(s) {
  if (!s || isNaN(s)) return '0:00'
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60).toString().padStart(2, '0')
  return `${m}:${sec}`
}
</script>

<template>
  <div class="view">
    <div class="tts-layout">
      <!-- Voice grid -->
      <div class="voice-col">
        <div class="voice-header">
          <span class="section-label">// Select Voice — {{ selectedVoice || 'none' }}</span>
          <input class="input search-input" v-model="searchQuery" placeholder="Search…" />
        </div>

        <div v-if="loadingVoices" class="voice-grid">
          <div v-for="n in 6" :key="n" class="voice-card">
            <SkeletonBlock width="40px" height="40px" style="border-radius:50%" />
            <SkeletonBlock width="80px" height="12px" style="margin-top:8px" />
          </div>
        </div>

        <div v-else class="voice-grid">
          <button
            v-for="v in filteredVoices"
            :key="v.name"
            class="voice-card"
            :class="{ selected: selectedVoice === v.name }"
            @click="selectVoice(v.name)"
          >
            <div class="voice-avatar" :style="{ background: voiceColor(v.name) }">
              {{ voiceInitials(v.name) }}
            </div>
            <span class="voice-name">{{ v.name }}</span>
            <span class="voice-gender badge badge-dim">{{ v.gender === 'F' ? 'F' : 'M' }}</span>
          </button>
        </div>
      </div>

      <!-- Input + result col -->
      <div class="input-col">
        <!-- Options row -->
        <div class="options-row">
          <div class="opt-group">
            <span class="opt-label">Format</span>
            <div class="mode-toggle">
              <button class="mode-btn" :class="{ active: selectedFormat === 'wav' }" @click="selectedFormat = 'wav'">WAV</button>
              <button class="mode-btn" :class="{ active: selectedFormat === 'mp3' }" @click="selectedFormat = 'mp3'">MP3</button>
            </div>
          </div>
          <div class="opt-group">
            <span class="opt-label">Speed</span>
            <span class="speed-note font-mono">// speed control coming soon</span>
          </div>
        </div>

        <!-- Textarea -->
        <div class="text-field">
          <textarea
            class="input textarea"
            v-model="text"
            placeholder="Enter the text to synthesize…"
            :disabled="isGenerating"
            :maxlength="MAX_CHARS"
          />
          <span class="char-count" :class="{ warn: charWarn }">{{ text.length }} / {{ MAX_CHARS }}</span>
        </div>

        <!-- Generate button -->
        <button
          class="btn btn-primary gen-btn"
          :disabled="isGenerating || !text.trim() || !selectedVoice"
          @click="generate"
        >
          <svg v-if="!isGenerating" width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          <span v-else class="spinner"></span>
          {{ isGenerating ? 'Generating…' : 'Generate Speech' }}
        </button>

        <!-- Progress -->
        <div v-if="isGenerating" class="prog-wrap">
          <div class="prog-track"><div class="prog-fill" :style="{ width: progressPct + '%' }"></div></div>
          <span class="prog-msg">{{ progressMsg }}</span>
        </div>

        <!-- Audio player -->
        <div v-if="audioUrl" class="audio-result">
          <audio
            ref="audioEl"
            :src="audioUrl"
            style="display:none"
            @timeupdate="onTimeUpdate"
            @loadedmetadata="onLoadedMetadata"
            @play="isPlaying = true"
            @pause="isPlaying = false"
            @ended="onEnded"
          />
          <div class="player">
            <button class="play-btn" @click="togglePlay">
              <svg v-if="!isPlaying" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
            </button>
            <div class="waveform-track" @click="scrub">
              <div class="waveform-progress" :style="{ width: duration ? (currentTime / duration * 100) + '%' : '0%' }"></div>
            </div>
            <span class="time-display">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
          </div>
          <a :href="audioUrl" :download="`tts.${audioFormat}`" class="btn btn-teal btn-sm">↓ Download {{ audioFormat.toUpperCase() }}</a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view { padding: 28px 32px; max-width: 1100px; }

.tts-layout { display: grid; grid-template-columns: 280px 1fr; gap: 24px; align-items: start; }

/* Voice col */
.voice-col { min-width: 0; }
.voice-header { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; }
.search-input { padding: 7px 10px; font-size: 12px; }

.voice-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; max-height: 520px; overflow-y: auto; }

.voice-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.1s;
}
.voice-card:hover { border-color: var(--b-amber); }
.voice-card.selected { border-color: var(--amber); background: var(--amber-g); }

.voice-avatar {
  width: 36px; height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  color: rgba(255,255,255,0.9);
  flex-shrink: 0;
}
.voice-name { font-size: 10px; font-family: var(--font-mono); color: var(--text); text-align: center; line-height: 1.3; }
.voice-gender { padding: 1px 5px; font-size: 9px; }

/* Input col */
.input-col { display: flex; flex-direction: column; gap: 16px; }
.options-row { display: flex; gap: 20px; align-items: center; }
.opt-group { display: flex; align-items: center; gap: 10px; }
.opt-label { font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }
.speed-note { font-size: 10px; color: var(--dim); }
.font-mono { font-family: var(--font-mono); }

.mode-toggle { display: flex; gap: 4px; }
.mode-btn { padding: 4px 10px; border-radius: var(--radius); font-size: 10px; font-family: var(--font-mono); background: var(--bg4); border: 1px solid var(--border); color: var(--muted); cursor: pointer; }
.mode-btn.active { background: var(--amber-g); border-color: var(--b-amber); color: var(--amber); }

.text-field { position: relative; }
.textarea { min-height: 200px; resize: vertical; line-height: 1.6; }
.char-count { position: absolute; bottom: 8px; right: 10px; font-family: var(--font-mono); font-size: 10px; color: var(--muted); }
.char-count.warn { color: var(--amber); }

.gen-btn { align-self: flex-start; display: flex; align-items: center; gap: 8px; }

.spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid rgba(0,0,0,0.2); border-top-color: #000; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.prog-wrap { display: flex; flex-direction: column; gap: 6px; }
.prog-track { height: 3px; background: var(--bg4); border-radius: 2px; overflow: hidden; }
.prog-fill { height: 100%; background: var(--amber); transition: width 0.3s; }
.prog-msg { font-size: 11px; font-family: var(--font-mono); color: var(--muted); }

/* Audio player */
.audio-result { display: flex; flex-direction: column; gap: 10px; padding: 16px; background: var(--bg3); border: 1px solid var(--b-teal); border-radius: var(--radius-lg); }
.player { display: flex; align-items: center; gap: 12px; }
.play-btn { width: 36px; height: 36px; border-radius: 50%; background: var(--amber); color: #000; display: flex; align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0; border: none; }
.play-btn:hover { opacity: 0.85; }
.waveform-track { flex: 1; height: 4px; background: var(--bg4); border-radius: 2px; cursor: pointer; overflow: hidden; position: relative; }
.waveform-progress { height: 100%; background: var(--amber); border-radius: 2px; transition: width 0.1s; }
.time-display { font-family: var(--font-mono); font-size: 10px; color: var(--muted); white-space: nowrap; flex-shrink: 0; }
</style>
