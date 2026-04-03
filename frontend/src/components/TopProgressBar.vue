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

<style scoped lang="scss">@use '../assets/scss/components/TopProgressBar';</style>
