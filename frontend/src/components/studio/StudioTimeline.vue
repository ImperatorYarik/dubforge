<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  videoId: { type: String, default: null },
  dubbedVideoId: { type: String, default: null },
  duration: { type: Number, default: 0 },
  currentTime: { type: Number, default: 0 },
})

const emit = defineEmits(['seek'])

const zoom = ref(1)

const playheadPercent = computed(() => {
  if (!props.duration) return 0
  return Math.min(100, (props.currentTime / props.duration) * 100)
})

function handleTimelineClick(event) {
  const el = event.currentTarget
  const rect = el.getBoundingClientRect()
  const offsetX = event.clientX - rect.left
  const ratio = rect.width > 0 ? offsetX / rect.width : 0
  emit('seek', ratio * props.duration)
}

const TRACKS = [
  { id: 'v1', label: 'V1', colorClass: 'studio-timeline__track-bar--video', testid: 'track-v1' },
  { id: 'a1', label: 'A1 Orig', colorClass: 'studio-timeline__track-bar--audio-orig', testid: 'track-a1' },
  { id: 'a2', label: 'A2 Dubbed', colorClass: 'studio-timeline__track-bar--audio-dubbed', testid: 'track-a2' },
]
</script>

<template>
  <div class="studio-timeline">
    <!-- Toolbar -->
    <div class="studio-timeline__toolbar">
      <button class="studio-timeline__tool-btn" data-testid="toolbar-cut" title="Cut">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <path d="M9.64 7.64A4 4 0 0 1 12 2a4 4 0 0 1 0 8 4 4 0 0 1-2.36-.64L8 11l1.64 1.64A4 4 0 0 1 12 12a4 4 0 0 1 0 8 4 4 0 0 1-2.36-7.64L8 11 3 6l1.5-1.5 5.14 3.14zm2.36.36a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm0 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4z" />
        </svg>
      </button>
      <button class="studio-timeline__tool-btn" data-testid="toolbar-trim" title="Trim">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <path d="M11 2H9L4 12l5 10h2l-5-10zm4 0h2l5 10-5 10h-2l5-10z" />
        </svg>
      </button>
      <button class="studio-timeline__tool-btn" data-testid="toolbar-undo" title="Undo">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z" />
        </svg>
      </button>
      <div class="studio-timeline__toolbar-spacer" />
      <input
        v-model="zoom"
        type="range"
        min="1"
        max="4"
        step="0.1"
        class="studio-timeline__zoom"
        data-testid="zoom-slider"
        title="Zoom"
      />
    </div>

    <!-- Tracks -->
    <div class="studio-timeline__tracks">
      <div
        v-for="track in TRACKS"
        :key="track.id"
        class="studio-timeline__track-row"
        :data-testid="track.testid"
      >
        <div class="studio-timeline__track-label">{{ track.label }}</div>
        <div
          class="studio-timeline__track-area"
          data-testid="timeline-area"
          @click="handleTimelineClick"
        >
          <div
            class="studio-timeline__track-bar"
            :class="track.colorClass"
          />
          <!-- Playhead -->
          <div
            v-if="track.id === 'v1'"
            class="studio-timeline__playhead"
            :style="{ left: `${playheadPercent}%` }"
            data-testid="playhead"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.studio-timeline {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg);
  border-top: 1px solid var(--border);
  overflow: hidden;

  &__toolbar {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 10px;
    border-bottom: 1px solid var(--border);
    background: var(--bg2);
    flex-shrink: 0;
  }

  &__tool-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: transparent;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--muted);
    cursor: pointer;
    transition: background 0.12s, color 0.12s;

    &:hover {
      background: var(--bg4);
      color: var(--text);
    }
  }

  &__toolbar-spacer {
    flex: 1;
  }

  &__zoom {
    width: 100px;
    accent-color: var(--amber);
  }

  &__tracks {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
  }

  &__track-row {
    display: flex;
    align-items: center;
    height: 36px;
    margin-bottom: 4px;
  }

  &__track-label {
    width: 70px;
    flex-shrink: 0;
    padding: 0 10px;
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--muted);
    user-select: none;
  }

  &__track-area {
    flex: 1;
    height: 28px;
    background: var(--bg3);
    border-radius: var(--radius);
    position: relative;
    cursor: pointer;
    overflow: visible;
  }

  &__track-bar {
    position: absolute;
    inset: 4px 8px;
    border-radius: 3px;
    opacity: 0.85;

    &--video {
      background: linear-gradient(90deg, #4a6fa5 0%, #6b8cbf 40%, #4a6fa5 100%);
    }

    &--audio-orig {
      background: repeating-linear-gradient(
        90deg,
        var(--amber) 0px,
        var(--amber) 2px,
        var(--amber-d) 2px,
        var(--amber-d) 6px
      );
      opacity: 0.7;
    }

    &--audio-dubbed {
      background: repeating-linear-gradient(
        90deg,
        var(--teal) 0px,
        var(--teal) 2px,
        transparent 2px,
        transparent 6px
      );
      opacity: 0.7;
    }
  }

  &__playhead {
    position: absolute;
    top: -8px;
    bottom: -8px;
    width: 2px;
    background: var(--red);
    transform: translateX(-50%);
    pointer-events: none;
    z-index: 10;

    &::before {
      content: '';
      position: absolute;
      top: -2px;
      left: 50%;
      transform: translateX(-50%);
      width: 8px;
      height: 8px;
      background: var(--red);
      border-radius: 50%;
    }
  }
}
</style>
