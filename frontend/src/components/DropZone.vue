<script setup>
import { ref } from 'vue'

const emit = defineEmits(['youtube-url', 'file'])

const url = ref('')
const dragging = ref(false)
const fileInput = ref(null)

function onDrop(e) {
  dragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) emit('file', file)
}

function onFileChange(e) {
  const file = e.target.files[0]
  if (file) emit('file', file)
}

function submit() {
  const v = url.value.trim()
  if (v) {
    emit('youtube-url', v)
    url.value = ''
  }
}
</script>

<template>
  <div class="wrap">
    <div
      class="zone"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave="dragging = false"
      @drop.prevent="onDrop"
      @click="fileInput?.click()"
    >
      <input ref="fileInput" type="file" accept="video/*" hidden @change="onFileChange" />
      <div class="icon">↑</div>
      <p class="label">Drag &amp; drop your video here</p>
      <p class="hint">MP4 or MOV</p>
    </div>

    <div class="url-row">
      <input
        v-model="url"
        class="input url-input"
        placeholder="https://youtube.com/watch?v=..."
        @keydown.enter="submit"
        @click.stop
      />
      <button class="btn btn-primary" :disabled="!url.trim()" @click.stop="submit">
        Import →
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.zone {
  border: 1.5px dashed var(--border);
  border-radius: var(--radius-lg);
  padding: 56px 40px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  background: var(--surface);
  user-select: none;
}

.zone:hover, .zone.dragging {
  border-color: #A1A1AA;
  background: var(--surface-subtle);
}

.icon {
  font-size: 28px;
  color: var(--text-placeholder);
  margin-bottom: 12px;
  line-height: 1;
}

.label {
  font-size: 15px;
  font-weight: 500;
  color: var(--text);
  margin-bottom: 4px;
}

.hint {
  font-size: 13px;
  color: var(--text-muted);
}

.url-row {
  display: flex;
  gap: 8px;
}
.url-input { flex: 1; }
</style>
