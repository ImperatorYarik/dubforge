<script setup>
import { RouterLink, useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const isActive = (path) => computed(() => route.path.startsWith(path))
</script>

<template>
  <header class="app-header">
    <RouterLink to="/" class="brand">
      <span class="brand-icon">🎬</span>
      <span>VideoTrans</span>
    </RouterLink>
    <nav>
      <RouterLink to="/projects" :class="{ active: isActive('/projects').value }">
        Projects
      </RouterLink>
      <RouterLink to="/videos" :class="{ active: isActive('/videos').value }">
        Videos
      </RouterLink>
    </nav>
  </header>
</template>

<style scoped lang="scss">@use '../assets/scss/components/AppHeader';</style>
