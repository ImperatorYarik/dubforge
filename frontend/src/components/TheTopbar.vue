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

<style scoped lang="scss">@use '../assets/scss/components/TheTopbar';</style>
