<script setup>
import TheSidebar from '@/components/TheSidebar.vue'
import AppToast from '@/components/AppToast.vue'
import TopProgressBar from '@/components/TopProgressBar.vue'
</script>

<template>
  <TopProgressBar />
  <div class="shell">
    <TheSidebar />
    <main class="main">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
  </div>
  <AppToast />
</template>

<style>
#app { height: 100%; }
.shell {
  display: flex;
  min-height: 100vh;
}
.main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
}
</style>
