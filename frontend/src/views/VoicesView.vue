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

function voiceColor(name) {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) & 0xffffffff
  const hue = Math.abs(hash) % 360
  return `hsl(${hue}, 45%, 28%)`
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
    // Poll for result
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
  // Stop all others
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
  <div class="view">
    <div class="page-header">
      <div>
        <h1 class="page-title">Voice Library</h1>
        <p class="page-sub">XTTS v2 built-in speakers · Click Preview to hear a sample</p>
      </div>
    </div>

    <!-- Language tabs -->
    <div class="lang-tabs">
      <button
        v-for="lang in langs"
        :key="lang"
        :class="['lang-tab', { active: langFilter === lang }]"
        @click="langFilter = lang"
      >{{ lang }}</button>
    </div>

    <!-- Grid -->
    <div v-if="loading" class="grid">
      <div v-for="n in 8" :key="n" class="voice-card">
        <SkeletonBlock width="44px" height="44px" style="border-radius:50%" />
        <div style="flex:1;display:flex;flex-direction:column;gap:6px;margin-top:4px">
          <SkeletonBlock width="120px" height="12px" />
          <SkeletonBlock width="60px" height="10px" />
        </div>
      </div>
    </div>

    <div v-else class="grid">
      <div v-for="v in filtered" :key="v.name" class="voice-card">
        <div class="voice-avatar" :style="{ background: voiceColor(v.name) }">
          {{ voiceInitials(v.name) }}
        </div>
        <div class="voice-info">
          <p class="voice-name">{{ v.name }}</p>
          <p class="voice-gender">{{ v.gender === 'F' ? 'Female' : 'Male' }}</p>
        </div>
        <button
          class="preview-btn"
          :class="{ loading: previewingVoice === v.name }"
          @click="preview(v)"
          :disabled="!!previewingVoice && previewingVoice !== v.name"
        >
          <svg v-if="previewingVoice !== v.name" width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          <span v-else class="spinner-sm"></span>
          {{ previewingVoice === v.name ? '…' : 'Preview' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.view { padding: 28px 32px; max-width: 1000px; }

.page-header { margin-bottom: 20px; }
.page-title { font-family: var(--font-display); font-size: 32px; letter-spacing: 0.04em; }
.page-sub { font-size: 12px; color: var(--muted); margin-top: 4px; }

.lang-tabs { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 20px; }
.lang-tab { padding: 5px 12px; border-radius: var(--radius); font-size: 11px; font-family: var(--font-mono); background: var(--bg4); border: 1px solid var(--border); color: var(--muted); cursor: pointer; letter-spacing: 0.06em; }
.lang-tab:hover { border-color: var(--b-amber); color: var(--text); }
.lang-tab.active { background: var(--amber-g); border-color: var(--b-amber); color: var(--amber); }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 8px; }

.voice-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  transition: border-color 0.1s;
}
.voice-card:hover { border-color: var(--b-amber); }

.voice-avatar {
  width: 40px; height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 500;
  color: rgb(255,255,255,0.9);
  flex-shrink: 0;
}

.voice-info { flex: 1; min-width: 0; }
.voice-name { font-size: 12.5px; font-weight: 500; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.voice-gender { font-size: 11px; color: var(--muted); margin-top: 2px; font-family: var(--font-mono); }

.preview-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border-radius: var(--radius);
  font-size: 10px;
  font-family: var(--font-mono);
  background: var(--bg4);
  border: 1px solid var(--border);
  color: var(--muted);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.1s;
}
.preview-btn:hover:not(:disabled) { border-color: var(--b-amber); color: var(--amber); }
.preview-btn:disabled { opacity: 0.4; }
.preview-btn.loading { border-color: var(--b-amber); color: var(--amber); }

.spinner-sm { display: inline-block; width: 10px; height: 10px; border: 1.5px solid rgb(232,160,32,0.3); border-top-color: var(--amber); border-radius: 50%; animation: spin 0.7s linear infinite; }

</style>
