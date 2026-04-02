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

<style scoped lang="scss">@use '../assets/scss/components/DropZone';</style>
