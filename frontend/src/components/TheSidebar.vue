<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()
const collapsed = ref(false)

const nav = [
  { label: 'Projects',        to: '/projects', icon: '⊞' },
  { label: 'Voices',          to: '/voices',   icon: '◎' },
  { label: 'Text to Speech',  to: '/tts',      icon: '♪' },
  { label: 'Settings',        to: '/settings', icon: '⚙' },
]
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="sidebar-top">
      <RouterLink to="/projects" class="logo">
        <span class="logo-mark">▶</span>
        <span v-if="!collapsed" class="logo-name">VideoTrans</span>
      </RouterLink>

      <button class="toggle-btn" :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'" @click="collapsed = !collapsed">
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
          <rect x="0.75" y="0.75" width="13.5" height="13.5" rx="2" stroke="currentColor" stroke-width="1.3"/>
          <line x1="4.5" y1="0.75" x2="4.5" y2="14.25" stroke="currentColor" stroke-width="1.3"/>
          <path v-if="!collapsed" d="M2 5.5L3.2 7.5 2 9.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
          <path v-else d="M3 5.5L1.8 7.5 3 9.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>

    <nav class="nav">
      <RouterLink
        v-for="item in nav"
        :key="item.to"
        :to="item.to"
        class="nav-link"
        :class="{ active: route.path.startsWith(item.to) }"
        :title="collapsed ? item.label : undefined"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
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
  background: var(--sidebar-bg);
  border-right: 1px solid var(--sidebar-border);
  display: flex;
  flex-direction: column;
  padding: 20px 12px;
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;
  transition: width 0.2s ease, padding 0.2s ease;
}
.sidebar.collapsed {
  width: 52px;
  padding: 20px 8px;
}

/* ── Top row: logo + toggle ── */
.sidebar-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 24px;
  gap: 6px;
  min-height: 42px;
}
.sidebar.collapsed .sidebar-top {
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding-bottom: 20px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--sidebar-text-active);
  overflow: hidden;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}
.sidebar.collapsed .logo { flex: none; }

.logo-mark { font-size: 14px; flex-shrink: 0; }
.logo-name {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.03em;
}

/* ── Toggle button ── */
.toggle-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 5px;
  color: var(--sidebar-text);
  background: transparent;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.1s, color 0.1s;
}
.toggle-btn:hover {
  background: var(--sidebar-hover-bg);
  color: var(--sidebar-text-active);
}

/* ── Nav ── */
.nav {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 10px;
  border-radius: var(--radius);
  font-size: 13.5px;
  font-weight: 500;
  color: var(--sidebar-text);
  transition: background 0.1s, color 0.1s;
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
}
.nav-link:hover { background: var(--sidebar-hover-bg); color: var(--sidebar-text-active); }
.nav-link.active { background: var(--sidebar-active-bg); color: var(--sidebar-text-active); }

.sidebar.collapsed .nav-link {
  padding: 8px;
  justify-content: center;
}

.nav-icon {
  font-size: 14px;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
  opacity: 0.7;
}
.nav-link.active .nav-icon,
.nav-link:hover .nav-icon { opacity: 1; }
</style>
