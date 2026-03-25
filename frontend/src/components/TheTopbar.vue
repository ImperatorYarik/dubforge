<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSystemStore } from '@/stores/system'

const route = useRoute()
const sys = useSystemStore()

const title = computed(() => route.meta?.title ?? 'DubForge')

const gpuBadge = computed(() => {
  if (!sys.gpuAvailable) return { cls: 'badge-err', label: 'No GPU' }
  const pct = sys.gpuMemoryTotalMb > 0 ? Math.round(sys.gpuMemoryUsedMb / sys.gpuMemoryTotalMb * 100) : 0
  return { cls: 'badge-ok', label: sys.gpuName ? `${sys.gpuName} · ${pct}%` : 'GPU' }
})

const modelBadge = computed(() => {
  if (!sys.workerOnline) return { cls: 'badge-err', label: 'WORKER OFFLINE' }
  if (sys.xttsLoaded) return { cls: 'badge-warn', label: 'XTTS LOADED' }
  if (sys.whisperLoaded) return { cls: 'badge-ok', label: 'WHISPER LOADED' }
  return { cls: 'badge-dim', label: 'IDLE' }
})
</script>

<template>
  <header class="topbar">
    <span class="topbar-title">{{ title }}</span>
    <div class="topbar-badges">
      <span :class="['badge', gpuBadge.cls]">
        <span class="badge-dot"></span>
        {{ gpuBadge.label }}
      </span>
      <span :class="['badge', modelBadge.cls]">
        <span class="badge-dot"></span>
        {{ modelBadge.label }}
      </span>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  height: var(--topbar-height);
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}
.topbar-title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}
.topbar-badges {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
