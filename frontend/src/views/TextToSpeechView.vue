<script setup>
import { ref, onMounted } from 'vue'
import * as ttsApi from '@/api/tts'
import { getProgressWsUrl } from '@/api/jobs'

const voices = ref([])
const selectedVoice = ref('')
const selectedFormat = ref('wav')
const text = ref('')
const isGenerating = ref(false)
const progress = ref({ pct: 0, message: '' })
const audioUrl = ref(null)
const audioFormat = ref('wav')
const error = ref(null)

onMounted(async () => {
  try {
    const { data } = await ttsApi.getVoices()
    voices.value = data
    if (data.length) selectedVoice.value = data[0].name
  } catch {
    error.value = 'Failed to load voices'
  }
})

function watchProgress(taskId) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(getProgressWsUrl(taskId))
    ws.onmessage = (e) => {
      const d = JSON.parse(e.data)
      progress.value = d
      if (d.pct >= 100) {
        ws.close()
        resolve()
      }
    }
    ws.onerror = () => {
      ws.close()
      reject(new Error('WebSocket connection failed'))
    }
  })
}

async function generate() {
  if (!text.value.trim() || !selectedVoice.value) return

  isGenerating.value = true
  audioUrl.value = null
  error.value = null
  progress.value = { pct: 0, message: 'Submitting...' }

  try {
    const { data } = await ttsApi.generateTts(text.value, selectedVoice.value, selectedFormat.value)
    await watchProgress(data.task_id)
    const { data: status } = await ttsApi.getTtsStatus(data.task_id)
    if (status.status === 'completed') {
      audioUrl.value = status.result.audio_url
      audioFormat.value = status.result.format
    } else {
      error.value = status.error || 'Generation failed'
    }
  } catch (e) {
    error.value = e.message
  } finally {
    isGenerating.value = false
  }
}
</script>

<template>
  <div class="view">
    <div class="page-header">
      <h1 class="page-title">Text to Speech</h1>
      <p class="page-sub">Synthesize speech using XTTS v2 built-in voices</p>
    </div>

    <div class="tts-layout">
      <!-- Voice + Format selectors -->
      <div class="controls-row">
        <div class="field field-voice">
          <label class="label">Voice</label>
          <select class="input select" v-model="selectedVoice" :disabled="isGenerating">
            <option v-for="v in voices" :key="v.name" :value="v.name">
              {{ v.name }} ({{ v.gender === 'F' ? 'Female' : 'Male' }})
            </option>
          </select>
        </div>
        <div class="field field-format">
          <label class="label">Format</label>
          <select class="input select" v-model="selectedFormat" :disabled="isGenerating">
            <option value="wav">WAV</option>
            <option value="mp3">MP3</option>
          </select>
        </div>
      </div>

      <!-- Text input -->
      <div class="field">
        <label class="label">Text</label>
        <textarea
          class="input textarea"
          v-model="text"
          placeholder="Enter the text you want to synthesize…"
          :disabled="isGenerating"
          maxlength="2000"
        />
        <p class="char-count">{{ text.length }} / 2000</p>
      </div>

      <!-- Generate button -->
      <button
        class="btn btn-primary generate-btn"
        :disabled="isGenerating || !text.trim() || !selectedVoice"
        @click="generate"
      >
        <span v-if="isGenerating" class="spinner" />
        {{ isGenerating ? 'Generating…' : 'Generate' }}
      </button>

      <!-- Progress -->
      <div v-if="isGenerating" class="progress-wrap">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progress.pct + '%' }" />
        </div>
        <p class="progress-msg">{{ progress.message }}</p>
      </div>

      <!-- Error -->
      <p v-if="error" class="error-msg">{{ error }}</p>

      <!-- Result -->
      <div v-if="audioUrl" class="result-wrap">
        <p class="result-label">Result</p>
        <audio class="audio-player" :src="audioUrl" controls />
        <a
          class="btn btn-ghost btn-sm"
          :href="audioUrl"
          :download="`tts-output.${audioFormat}`"
        >
          Download {{ audioFormat.toUpperCase() }}
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view {
  padding: 40px 48px;
  max-width: 760px;
}

.page-header { margin-bottom: 32px; }
.page-title { font-size: 20px; font-weight: 600; letter-spacing: -0.025em; }
.page-sub { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

.tts-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.controls-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.field { display: flex; flex-direction: column; gap: 6px; }
.field-voice { flex: 1; }
.field-format { width: 120px; flex-shrink: 0; }

.label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  letter-spacing: 0.02em;
}

.select {
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L5 5L9 1' stroke='%236B6B6B' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  padding-right: 28px;
}

.textarea {
  min-height: 220px;
  resize: vertical;
  font-family: inherit;
  line-height: 1.6;
}

.char-count {
  font-size: 11.5px;
  color: var(--text-placeholder);
  text-align: right;
  margin: 0;
}

.generate-btn {
  align-self: flex-start;
  display: flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  display: inline-block;
  width: 13px;
  height: 13px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.progress-wrap { display: flex; flex-direction: column; gap: 6px; }
.progress-bar {
  height: 4px;
  background: var(--border);
  border-radius: 99px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 99px;
  transition: width 0.3s ease;
}
.progress-msg {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.error-msg {
  font-size: 13px;
  color: #c0392b;
  margin: 0;
  padding: 10px 14px;
  background: #fdf2f2;
  border: 1px solid #f5c6c6;
  border-radius: var(--radius);
}

.result-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface-subtle);
}
.result-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin: 0;
}
.audio-player {
  width: 100%;
  height: 40px;
  border-radius: var(--radius);
}
</style>
