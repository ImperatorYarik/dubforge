<script setup>
import { computed } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useVideosStore } from '@/stores/videos'
import { useJobsStore } from '@/stores/jobs'

const active = computed(() =>
  useProjectsStore().loading || useVideosStore().loading || useJobsStore().loading
)
</script>

<template>
  <div class="bar-wrap">
    <Transition name="fade">
      <div v-if="active" class="bar" />
    </Transition>
  </div>
</template>

<style scoped>
.bar-wrap {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 2px;
  z-index: 9999;
  pointer-events: none;
}
.bar {
  height: 100%;
  background: var(--accent);
  animation: load 1.6s ease-in-out infinite;
}
@keyframes load {
  0%   { width: 0%;  margin-left: 0;    opacity: 1; }
  60%  { width: 75%; margin-left: 0; }
  100% { width: 0%;  margin-left: 100%; opacity: 0; }
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
