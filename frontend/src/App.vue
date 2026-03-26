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
  <div class="shell">
    <TheSidebar />
    <div class="main-col">
      <TheTopbar />
      <div v-if="!systemStore.workerOnline" class="worker-banner">
        <span>⚠</span> Worker offline — jobs will queue when worker comes online
      </div>
      <main class="main">
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

<style lang="scss">
#app { height: 100%; }

.shell {
  display: flex;
  min-height: 100vh;
}

.main-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.main {
  flex: 1;
  overflow-y: auto;
}
</style>
