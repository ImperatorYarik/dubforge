<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSystemStore } from '@/stores/system'
import { useProjectsStore } from '@/stores/projects'

const route = useRoute()
const sys = useSystemStore()
const projectsStore = useProjectsStore()

const title = computed(() => route.meta?.title ?? 'DubForge')
const projectName = computed(() => projectsStore.currentProject?.metadata?.title ?? null)

const gpuBadge = computed(() => {
  if (!sys.gpuAvailable) return { cls: 'badge-err', label: 'No GPU' }
  const pct = sys.gpuMemoryTotalMb > 0 ? Math.round(sys.gpuMemoryUsedMb / sys.gpuMemoryTotalMb * 100) : 0
  return { cls: 'badge-ok', label: sys.gpuName ? `${sys.gpuName} · ${pct}%` : 'GPU' }
})

const modelBadge = computed(() => {
  if (!sys.workerOnline) return { cls: 'badge-warn', label: 'WORKER OFFLINE' }
  if (sys.xttsLoaded) return { cls: 'badge-warn', label: 'XTTS LOADED' }
  if (sys.whisperLoaded) return { cls: 'badge-ok', label: 'WHISPER LOADED' }
  return { cls: 'badge-dim', label: 'IDLE' }
})
</script>

<template>
  <header class="topbar">
    <div class="topbar-left">
      <span class="topbar-title">{{ title }}</span>
      <span v-if="projectName" class="topbar-project">{{ projectName }}</span>
    </div>
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

<style scoped lang="scss">
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

.topbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.topbar-title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.topbar-project {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 500;
  color: var(--text);
  opacity: 0.7;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 280px;
}

.topbar-project::before {
  content: '·';
  margin-right: 10px;
  color: var(--dim);
}

.topbar-badges {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
