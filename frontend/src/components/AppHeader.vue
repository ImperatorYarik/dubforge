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

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  height: 60px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 100;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.2rem;
  font-weight: 700;
  text-decoration: none;
  color: var(--color-text);
}

.brand-icon {
  font-size: 1.4rem;
}

nav {
  display: flex;
  gap: 0.25rem;
}

nav a {
  padding: 0.4rem 0.9rem;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-muted);
  text-decoration: none;
  transition: background 0.15s, color 0.15s;
}

nav a:hover,
nav a.active,
nav a.router-link-active {
  background: var(--color-accent-muted);
  color: var(--color-accent);
}
</style>
