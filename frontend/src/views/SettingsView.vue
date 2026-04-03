<script setup>
import { ref } from 'vue'

const srtEnabled   = ref(true)
const resolution   = ref('1080p')
const removeAudio  = ref(true)

const resolutions = ['720p', '1080p', '4K']
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
</script>

<template>
  <div class="view">
    <div class="page-header">
      <h1 class="page-title">Settings</h1>
    </div>

    <div class="sections">
      <!-- Export -->
      <section class="card">
        <h2 class="card-title">Export</h2>

        <div class="row">
          <div class="row-info">
            <p class="label">Output Resolution</p>
            <p class="desc">Target resolution for the dubbed video.</p>
          </div>
          <select v-model="resolution" class="select">
            <option v-for="r in resolutions" :key="r" :value="r">{{ r }}</option>
          </select>
        </div>

        <div class="row">
          <div class="row-info">
            <p class="label">Generate SRT subtitles</p>
            <p class="desc">Export a .srt file alongside the dubbed video.</p>
          </div>
          <label class="toggle">
            <input v-model="srtEnabled" type="checkbox" hidden />
            <span class="track" :class="{ on: srtEnabled }" />
          </label>
        </div>

        <div class="row">
          <div class="row-info">
            <p class="label">Remove original audio</p>
            <p class="desc">Replace original soundtrack entirely with the dubbed voice.</p>
          </div>
          <label class="toggle">
            <input v-model="removeAudio" type="checkbox" hidden />
            <span class="track" :class="{ on: removeAudio }" />
          </label>
        </div>
      </section>

      <!-- API -->
      <section class="card">
        <h2 class="card-title">API</h2>
        <div class="kv-list">
          <div class="kv"><span class="key">Backend URL</span><code class="val">{{ apiBaseUrl }}</code></div>
          <div class="kv"><span class="key">Model</span><code class="val">XTTS v2 · Whisper large-v3</code></div>
        </div>
      </section>
    </div>
  </div>
</template>


<style scoped lang="scss">
@use '../assets/scss/views/SettingsView';
</style>
