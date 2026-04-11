<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'

const route = useRoute()
const projectsStore = useProjectsStore()

const title = computed(() => route.meta?.title ?? 'DubForge')
const projectName = computed(() => projectsStore.currentProject?.metadata?.title ?? null)
</script>

<template>
  <header class="topbar">
    <div class="topbar-left">
      <span class="topbar-title">{{ title }}</span>
      <span v-if="projectName" class="topbar-project">{{ projectName }}</span>
    </div>
  </header>
</template>

<style scoped lang="scss">@use '../assets/scss/components/TheTopbar';</style>
