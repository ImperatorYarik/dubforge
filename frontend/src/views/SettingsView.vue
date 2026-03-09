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

<style scoped>
.view { padding: 40px 48px; max-width: 680px; }

.page-header { margin-bottom: 28px; }
.page-title { font-size: 20px; font-weight: 600; letter-spacing: -0.025em; }

.sections { display: flex; flex-direction: column; gap: 16px; }

.card {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  overflow: hidden;
}
.card-title {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: -0.01em;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
}
.row:last-child { border-bottom: none; }

.row-info { flex: 1; }
.label { font-size: 13.5px; font-weight: 500; }
.desc  { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.select {
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  outline: none;
}

/* Toggle */
.toggle { cursor: pointer; }
.track {
  display: block;
  width: 36px;
  height: 20px;
  border-radius: 99px;
  background: var(--border);
  position: relative;
  transition: background 0.2s;
}
.track::after {
  content: '';
  position: absolute;
  top: 3px; left: 3px;
  width: 14px; height: 14px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
  transition: transform 0.2s;
}
.track.on { background: var(--accent); }
.track.on::after { transform: translateX(16px); }

/* KV list */
.kv-list { padding: 4px 0; }
.kv {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
}
.kv:last-child { border-bottom: none; }
.key { font-size: 13px; color: var(--text-muted); width: 120px; flex-shrink: 0; }
.val { font-size: 12.5px; font-family: monospace; color: var(--text); }
</style>
