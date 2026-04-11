<script setup>
import { ref } from 'vue'

const props = defineProps({
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['generate-dub'])

const LANGUAGES = [
  { value: 'english', label: 'English' },
  { value: 'spanish', label: 'Spanish (Spain)' },
  { value: 'french', label: 'French' },
  { value: 'german', label: 'German' },
  { value: 'italian', label: 'Italian' },
  { value: 'portuguese', label: 'Portuguese' },
  { value: 'japanese', label: 'Japanese' },
  { value: 'korean', label: 'Korean' },
  { value: 'chinese', label: 'Chinese' },
  { value: 'arabic', label: 'Arabic' },
  { value: 'russian', label: 'Russian' },
  { value: 'hindi', label: 'Hindi' },
]

const targetLanguage = ref('spanish')
const voiceMode = ref('clone') // 'clone' | 'library'
const emotionPreservation = ref(true)
const pacingMatch = ref(true)
const lipSync = ref(false)

function handleGenerate() {
  emit('generate-dub', {
    targetLanguage: targetLanguage.value,
    voiceMode: voiceMode.value,
    emotionPreservation: emotionPreservation.value,
    pacingMatch: pacingMatch.value,
    lipSync: lipSync.value,
  })
}
</script>

<template>
  <div class="ai-dubbing-panel">
    <header class="ai-dubbing-panel__header">
      <span class="ai-dubbing-panel__header-label">AI Dubbing Studio</span>
    </header>

    <!-- Target Language -->
    <section class="ai-dubbing-panel__section">
      <h3 class="ai-dubbing-panel__section-title">TARGET LANGUAGE</h3>
      <select
        v-model="targetLanguage"
        class="ai-dubbing-panel__select"
        data-testid="language-select"
      >
        <option
          v-for="lang in LANGUAGES"
          :key="lang.value"
          :value="lang.value"
        >
          {{ lang.label }}
        </option>
      </select>
    </section>

    <!-- Voice Profile -->
    <section class="ai-dubbing-panel__section">
      <h3 class="ai-dubbing-panel__section-title">VOICE PROFILE</h3>
      <div class="ai-dubbing-panel__voice-tabs">
        <button
          class="ai-dubbing-panel__voice-tab"
          :class="{ 'ai-dubbing-panel__voice-tab--active': voiceMode === 'clone' }"
          data-testid="voice-tab-clone"
          @click="voiceMode = 'clone'"
        >
          Clone Original
        </button>
        <button
          class="ai-dubbing-panel__voice-tab"
          :class="{ 'ai-dubbing-panel__voice-tab--active': voiceMode === 'library' }"
          data-testid="voice-tab-library"
          @click="voiceMode = 'library'"
        >
          Library Voice
        </button>
      </div>
    </section>

    <!-- Toggles -->
    <section class="ai-dubbing-panel__section">
      <div class="ai-dubbing-panel__toggle-row">
        <label class="ai-dubbing-panel__toggle-label" for="toggle-emotion">
          Emotion Preservation
        </label>
        <input
          id="toggle-emotion"
          v-model="emotionPreservation"
          type="checkbox"
          class="ai-dubbing-panel__toggle"
          data-testid="toggle-emotion"
        />
      </div>

      <div class="ai-dubbing-panel__toggle-row">
        <label class="ai-dubbing-panel__toggle-label" for="toggle-pacing">
          Pacing Match
        </label>
        <input
          id="toggle-pacing"
          v-model="pacingMatch"
          type="checkbox"
          class="ai-dubbing-panel__toggle"
          data-testid="toggle-pacing"
        />
      </div>
    </section>

    <!-- Visual Sync -->
    <section class="ai-dubbing-panel__section">
      <h3 class="ai-dubbing-panel__section-title">VISUAL SYNC</h3>
      <div class="ai-dubbing-panel__toggle-row">
        <div class="ai-dubbing-panel__sync-info">
          <span class="ai-dubbing-panel__sync-icon">&#9654;</span>
          <div>
            <div class="ai-dubbing-panel__toggle-label">AI Lip-Sync</div>
            <div class="ai-dubbing-panel__sync-sub">Match mouth movements</div>
          </div>
        </div>
        <input
          id="toggle-lipsync"
          v-model="lipSync"
          type="checkbox"
          class="ai-dubbing-panel__toggle"
          data-testid="toggle-lipsync"
        />
      </div>
    </section>

    <!-- CTA -->
    <button
      class="btn btn-primary ai-dubbing-panel__cta"
      :disabled="loading"
      data-testid="btn-generate-dub"
      @click="handleGenerate"
    >
      <span v-if="loading" class="ai-dubbing-panel__spinner" aria-hidden="true" />
      <span v-else>&#9889;</span>
      Generate Dub
    </button>
  </div>
</template>

<style scoped lang="scss">
.ai-dubbing-panel {
  display: flex;
  flex-direction: column;
  gap: 0;
  height: 100%;
  overflow-y: auto;
  background: var(--bg2);
  padding: 16px;

  &__header {
    margin-bottom: 16px;
  }

  &__header-label {
    font-family: var(--font-display);
    font-size: 14px;
    letter-spacing: 0.08em;
    color: var(--muted);
    text-transform: uppercase;
  }

  &__section {
    margin-bottom: 20px;
  }

  &__section-title {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.12em;
    color: var(--muted);
    text-transform: uppercase;
    margin: 0 0 8px;
  }

  &__select {
    width: 100%;
    background: var(--bg4);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-family: var(--font-body);
    font-size: 13px;
    padding: 8px 10px;
    outline: none;
    cursor: pointer;

    &:focus {
      border-color: var(--b-amber);
    }
  }

  &__voice-tabs {
    display: flex;
    gap: 4px;
  }

  &__voice-tab {
    flex: 1;
    padding: 6px 8px;
    font-size: 11px;
    font-family: var(--font-mono);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    background: var(--bg4);
    color: var(--muted);
    cursor: pointer;
    transition: background 0.15s, color 0.15s, border-color 0.15s;

    &--active {
      background: var(--amber-g);
      border-color: var(--b-amber);
      color: var(--amber);
    }
  }

  &__toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);

    &:last-child {
      border-bottom: none;
    }
  }

  &__toggle-label {
    font-size: 12px;
    color: var(--text);
    font-family: var(--font-body);
    cursor: pointer;
  }

  &__toggle {
    width: 36px;
    height: 20px;
    appearance: none;
    background: var(--dim);
    border-radius: 10px;
    position: relative;
    cursor: pointer;
    transition: background 0.2s;
    flex-shrink: 0;

    &::after {
      content: '';
      position: absolute;
      width: 14px;
      height: 14px;
      background: var(--muted);
      border-radius: 50%;
      top: 3px;
      left: 3px;
      transition: left 0.2s, background 0.2s;
    }

    &:checked {
      background: var(--amber-g);

      &::after {
        left: 19px;
        background: var(--amber);
      }
    }
  }

  &__sync-info {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__sync-icon {
    color: var(--teal);
    font-size: 14px;
  }

  &__sync-sub {
    font-size: 10px;
    color: var(--muted);
    margin-top: 2px;
  }

  &__cta {
    margin-top: auto;
    width: 100%;
    justify-content: center;
    padding: 12px;
    font-size: 13px;
  }

  &__spinner {
    display: inline-block;
    width: 12px;
    height: 12px;
    border: 2px solid rgba(0, 0, 0, 0.3);
    border-top-color: #000;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
}
</style>
