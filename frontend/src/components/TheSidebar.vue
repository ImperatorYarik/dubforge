<script setup>
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()

const nav = [
  { label: 'Projects', to: '/projects' },
  { label: 'Voices',   to: '/voices' },
  { label: 'Settings', to: '/settings' },
]
</script>

<template>
  <aside class="sidebar">
    <RouterLink to="/projects" class="logo">
      <span class="logo-mark">▶</span>
      <span class="logo-name">VideoTrans</span>
    </RouterLink>

    <nav class="nav">
      <RouterLink
        v-for="item in nav"
        :key="item.to"
        :to="item.to"
        class="nav-link"
        :class="{ active: route.path.startsWith(item.to) }"
      >
        {{ item.label }}
      </RouterLink>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  min-height: 100vh;
  height: 100vh;
  position: sticky;
  top: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 20px 12px;
  overflow-y: auto;
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 6px 12px 28px;
  color: var(--text);
}
.logo-mark { font-size: 15px; }
.logo-name {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.025em;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.nav-link {
  display: block;
  padding: 8px 12px;
  border-radius: var(--radius);
  font-size: 13.5px;
  font-weight: 500;
  color: var(--text-muted);
  transition: background 0.1s, color 0.1s;
  letter-spacing: -0.01em;
}
.nav-link:hover { background: var(--surface-subtle); color: var(--text); }
.nav-link.active { background: var(--surface-subtle); color: var(--text); }
</style>
