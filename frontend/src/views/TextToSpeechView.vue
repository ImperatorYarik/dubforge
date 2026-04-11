<script setup>
import { ref, computed, onMounted } from 'vue'
import * as ttsApi from '@/api/tts'
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

async function generate() {
  if (!text.value.trim() || !selectedVoice.value) return
  isGenerating.value = true
  audioUrl.value = null
  progressPct.value = 0
  progressMsg.value = 'Submitting…'

  try {
    const { data } = await ttsApi.generateTts(text.value, selectedVoice.value, selectedFormat.value)
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
  <div class="tts-view">

    <div class="tts-view__header">
      <div>
        <h1 class="tts-view__title">Text to Speech</h1>
        <p class="tts-view__subtitle">Generate speech from text using XTTS v2 built-in voices</p>
      </div>
    </div>

    <div class="tts-view__layout">

      <!-- Left: text input + controls -->
      <div class="tts-view__input-col">

        <!-- Text area -->
        <div class="tts-view__text-field">
          <textarea
            class="input textarea tts-view__textarea"
            v-model="text"
            placeholder="Enter the text you want to synthesize…"
            :disabled="isGenerating"
            :maxlength="MAX_CHARS"
            data-testid="tts-textarea"
          />
          <span
            class="tts-view__char-count"
            :class="{ 'tts-view__char-count--warn': charWarn }"
            data-testid="char-count"
          >{{ text.length }} / {{ MAX_CHARS }}</span>
        </div>

        <!-- Format and options row -->
        <div class="tts-view__options">
          <div class="tts-view__option-group">
            <span class="tts-view__option-label">Format</span>
            <div class="tts-view__format-toggle">
              <button
                class="tts-view__format-btn"
                :class="{ 'tts-view__format-btn--active': selectedFormat === 'wav' }"
                data-testid="format-wav"
                @click="selectedFormat = 'wav'"
              >WAV</button>
              <button
                class="tts-view__format-btn"
                :class="{ 'tts-view__format-btn--active': selectedFormat === 'mp3' }"
                data-testid="format-mp3"
                @click="selectedFormat = 'mp3'"
              >MP3</button>
            </div>
          </div>
        </div>

        <!-- Generate button -->
        <button
          class="btn btn-primary tts-view__generate-btn"
          :disabled="isGenerating || !text.trim() || !selectedVoice"
          data-testid="generate-btn"
          @click="generate"
        >
          <span v-if="isGenerating" class="tts-view__spinner"></span>
          {{ isGenerating ? 'Generating…' : 'Generate Audio' }}
        </button>

        <!-- Progress -->
        <div v-if="isGenerating" class="tts-view__progress">
          <div class="tts-view__progress-track">
            <div class="tts-view__progress-fill" :style="{ width: progressPct + '%' }"></div>
          </div>
          <span class="tts-view__progress-msg">{{ progressMsg }}</span>
        </div>

        <!-- Audio player -->
        <div v-if="audioUrl" class="tts-view__audio-result">
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
          <div class="tts-view__player">
            <button class="tts-view__play-btn" @click="togglePlay">
              <svg v-if="!isPlaying" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>
              </svg>
            </button>
            <div class="tts-view__waveform" @click="scrub">
              <div
                class="tts-view__waveform-progress"
                :style="{ width: duration ? (currentTime / duration * 100) + '%' : '0%' }"
              ></div>
            </div>
            <span class="tts-view__time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
          </div>
          <a :href="audioUrl" :download="`tts.${audioFormat}`" class="btn btn-ghost btn-sm">
            Download {{ audioFormat.toUpperCase() }}
          </a>
        </div>

      </div>

      <!-- Right: voice selection -->
      <div class="tts-view__voice-col" data-testid="voice-select">

        <div class="tts-view__voice-header">
          <span class="tts-view__voice-label">
            Select Voice
            <span v-if="selectedVoice" class="tts-view__voice-selected">— {{ selectedVoice }}</span>
          </span>
          <input
            class="input tts-view__voice-search"
            v-model="searchQuery"
            placeholder="Search voices…"
          />
        </div>

        <div v-if="loadingVoices" class="tts-view__voice-grid">
          <div v-for="n in 8" :key="n" class="tts-view__voice-card tts-view__voice-card--skeleton">
            <SkeletonBlock width="40px" height="40px" style="border-radius: 50%" />
            <SkeletonBlock width="80px" height="12px" style="margin-top: 8px" />
          </div>
        </div>

        <div v-else class="tts-view__voice-grid">
          <button
            v-for="v in filteredVoices"
            :key="v.name"
            class="tts-view__voice-card"
            :class="{ 'tts-view__voice-card--selected': selectedVoice === v.name }"
            @click="selectVoice(v.name)"
          >
            <div class="tts-view__voice-avatar">{{ voiceInitials(v.name) }}</div>
            <span class="tts-view__voice-name">{{ v.name }}</span>
            <span class="tts-view__voice-gender">{{ v.gender === 'F' ? 'F' : 'M' }}</span>
          </button>
        </div>

      </div>

    </div>
  </div>
</template>

<style scoped lang="scss">
@use '../assets/scss/views/TextToSpeechView';
</style>
