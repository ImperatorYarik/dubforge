<script setup>
import AppHeader from '@/components/AppHeader.vue'
import AppToast from '@/components/AppToast.vue'
</script>

<template>
  <div class="app-layout">
    <AppHeader />
    <main class="main-content">
      <RouterView />
    </main>
    <AppToast />
  </div>
</template>

<style>
/* Global layout is in assets/main.css */
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
}

.main-content {
  flex: 1;
  padding: 2rem;
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}
</style>
