<script setup>
import { ref, computed, onMounted } from 'vue'
import * as ttsApi from '@/api/tts'
import { useToast } from '@/composables/useToast'
import SkeletonBlock from '@/components/SkeletonBlock.vue'

const toast = useToast()
const voices = ref([])
const loading = ref(true)
const langFilter = ref('ALL')
const previewingVoice = ref(null)
const previewUrls = ref({})
const previewAudios = ref({})

onMounted(async () => {
  try {
    const { data } = await ttsApi.getVoices()
    voices.value = data
  } catch {
    toast.error('Failed to load voices')
  } finally {
    loading.value = false
  }
})

const langs = computed(() => {
  const set = new Set(voices.value.map(v => v.language || 'EN'))
  return ['ALL', ...Array.from(set).sort()]
})

const filtered = computed(() => {
  if (langFilter.value === 'ALL') return voices.value
  return voices.value.filter(v => (v.language || 'EN') === langFilter.value)
})

function voiceInitials(name) {
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

async function preview(voice) {
  if (previewingVoice.value === voice.name) return
  previewingVoice.value = voice.name

  try {
    if (previewUrls.value[voice.name]) {
      playAudio(voice.name, previewUrls.value[voice.name])
      return
    }
    const { data } = await ttsApi.generateTts('Hello, this is a voice preview.', voice.name, 'mp3')
    const result = await pollStatus(data.task_id)
    if (result?.audio_url) {
      previewUrls.value[voice.name] = result.audio_url
      playAudio(voice.name, result.audio_url)
    }
  } catch {
    toast.error(`Preview failed for ${voice.name}`)
  } finally {
    if (previewingVoice.value === voice.name) previewingVoice.value = null
  }
}

async function pollStatus(taskId) {
  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 1500))
    const { data } = await ttsApi.getTtsStatus(taskId)
    if (data.status === 'completed') return data.result
    if (data.status === 'failed') throw new Error(data.error)
  }
  throw new Error('Timed out')
}

function playAudio(name, url) {
  Object.values(previewAudios.value).forEach(a => { a.pause(); a.currentTime = 0 })
  let audio = previewAudios.value[name]
  if (!audio) {
    audio = new Audio(url)
    previewAudios.value[name] = audio
  }
  audio.play()
}
</script>

<template>
  <div class="voices-view">

    <div class="voices-view__header">
      <div>
        <h1 class="voices-view__title">Voice Library</h1>
        <p class="voices-view__subtitle">XTTS v2 built-in speakers — click Preview to hear a sample</p>
      </div>
    </div>

    <!-- Language filter tabs -->
    <div class="voices-view__lang-filters" data-testid="lang-filters">
      <button
        v-for="lang in langs"
        :key="lang"
        class="voices-view__lang-tab"
        :class="{ 'voices-view__lang-tab--active': langFilter === lang }"
        @click="langFilter = lang"
      >
        {{ lang }}
      </button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="voices-view__grid">
      <div v-for="n in 8" :key="n" class="voices-view__card voices-view__card--skeleton">
        <SkeletonBlock width="44px" height="44px" style="border-radius: 50%; flex-shrink: 0" />
        <div class="voices-view__card-info">
          <SkeletonBlock width="120px" height="13px" />
          <SkeletonBlock width="60px" height="11px" style="margin-top: 6px" />
        </div>
      </div>
    </div>

    <!-- Voices grid -->
    <div v-else class="voices-view__grid">
      <div
        v-for="v in filtered"
        :key="v.name"
        class="voices-view__card"
        data-testid="voice-card"
      >
        <div class="voices-view__avatar">{{ voiceInitials(v.name) }}</div>
        <div class="voices-view__card-info">
          <p class="voices-view__name">{{ v.name }}</p>
          <p class="voices-view__gender">{{ v.gender === 'F' ? 'Female' : 'Male' }}</p>
        </div>
        <button
          class="btn btn-ghost btn-sm voices-view__preview-btn"
          :class="{ 'voices-view__preview-btn--loading': previewingVoice === v.name }"
          data-testid="preview-btn"
          :disabled="!!previewingVoice && previewingVoice !== v.name"
          @click="preview(v)"
        >
          <span v-if="previewingVoice === v.name" class="voices-view__spinner"></span>
          <svg v-else width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          {{ previewingVoice === v.name ? 'Loading…' : 'Preview' }}
        </button>
      </div>
    </div>

    <!-- Empty filtered state -->
    <div v-if="!loading && filtered.length === 0" class="voices-view__empty">
      <p>No voices for this language.</p>
    </div>

  </div>
</template>

<style scoped lang="scss">
@use '../assets/scss/views/VoicesView';
</style>
