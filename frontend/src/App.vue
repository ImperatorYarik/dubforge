<script setup>
import { onMounted, onUnmounted } from 'vue'
import TheSidebar from '@/components/TheSidebar.vue'
import AppToast from '@/components/AppToast.vue'
import TopProgressBar from '@/components/TopProgressBar.vue'
import TheTopbar from '@/components/TheTopbar.vue'
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()
let pollInterval = null

onMounted(() => {
  systemStore.fetchStatus()
  pollInterval = setInterval(() => systemStore.fetchStatus(), 30_000)
})

onUnmounted(() => {
  clearInterval(pollInterval)
})
</script>

<template>
  <TopProgressBar />
  <div class="app-shell">
    <TheSidebar />
    <div class="app-main-col">
      <TheTopbar />
      <div v-if="!systemStore.workerOnline" class="worker-banner">
        <span>⚠</span> Worker offline — jobs will queue when worker comes online
      </div>
      <main class="app-main">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
  <AppToast />
</template>

<style lang="scss">@use './assets/scss/views/App';</style>
