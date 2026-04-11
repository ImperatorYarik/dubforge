<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  videos: { type: Array, default: () => [] },
  activeVideoId: { type: String, default: null },
})

const emit = defineEmits(['select-video'])

const activeTab = ref('video') // 'video' | 'audio' | 'text'

const displayedVideos = computed(() => {
  if (activeTab.value === 'video') return props.videos
  return []
})

function formatDate(isoString) {
  if (!isoString) return ''
  const d = new Date(isoString)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

<template>
  <div class="media-assets-panel">
    <header class="media-assets-panel__header">
      <span class="media-assets-panel__title">MEDIA ASSETS</span>
    </header>

    <!-- Tabs -->
    <div class="media-assets-panel__tabs">
      <button
        class="media-assets-panel__tab"
        :class="{ 'media-assets-panel__tab--active': activeTab === 'video' }"
        data-testid="tab-video"
        @click="activeTab = 'video'"
      >
        Video
      </button>
      <button
        class="media-assets-panel__tab"
        :class="{ 'media-assets-panel__tab--active': activeTab === 'audio' }"
        data-testid="tab-audio"
        @click="activeTab = 'audio'"
      >
        Audio
      </button>
      <button
        class="media-assets-panel__tab"
        :class="{ 'media-assets-panel__tab--active': activeTab === 'text' }"
        data-testid="tab-text"
        @click="activeTab = 'text'"
      >
        Text
      </button>
    </div>

    <!-- Asset list -->
    <div class="media-assets-panel__list">
      <template v-if="displayedVideos.length > 0">
        <button
          v-for="video in displayedVideos"
          :key="video.video_id"
          class="media-assets-panel__asset-item"
          :class="{ 'media-assets-panel__asset-item--active': activeVideoId === video.video_id }"
          data-testid="asset-item"
          @click="emit('select-video', video.video_id)"
        >
          <div class="media-assets-panel__thumb" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
          <div class="media-assets-panel__info">
            <div class="media-assets-panel__filename">{{ video.original_filename || video.video_id }}</div>
            <div class="media-assets-panel__date">{{ formatDate(video.created_at) }}</div>
          </div>
        </button>
      </template>

      <div
        v-else
        class="media-assets-panel__empty"
        data-testid="assets-empty"
      >
        No assets yet
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.media-assets-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg2);
  border-right: 1px solid var(--border);
  overflow: hidden;

  &__header {
    padding: 14px 12px 10px;
    border-bottom: 1px solid var(--border);
  }

  &__title {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.12em;
    color: var(--muted);
    text-transform: uppercase;
  }

  &__tabs {
    display: flex;
    border-bottom: 1px solid var(--border);
  }

  &__tab {
    flex: 1;
    padding: 8px 4px;
    font-size: 11px;
    font-family: var(--font-mono);
    background: transparent;
    border: none;
    color: var(--muted);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: color 0.15s, border-color 0.15s;

    &--active {
      color: var(--amber);
      border-bottom-color: var(--amber);
    }

    &:hover:not(&--active) {
      color: var(--text);
    }
  }

  &__list {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
  }

  &__asset-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 8px 12px;
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    cursor: pointer;
    text-align: left;
    transition: background 0.12s, border-color 0.12s;

    &:hover {
      background: var(--bg4);
    }

    &--active {
      background: var(--amber-g);
      border-left-color: var(--amber);
    }
  }

  &__thumb {
    width: 36px;
    height: 28px;
    background: var(--bg4);
    border-radius: var(--radius);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    color: var(--muted);
  }

  &__info {
    min-width: 0;
    flex: 1;
  }

  &__filename {
    font-size: 11px;
    color: var(--text);
    font-family: var(--font-mono);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__date {
    font-size: 10px;
    color: var(--muted);
    margin-top: 2px;
  }

  &__empty {
    padding: 24px 12px;
    text-align: center;
    font-size: 12px;
    color: var(--muted);
    font-family: var(--font-body);
  }
}
</style>
