<script setup>
import { RouterLink } from 'vue-router'

defineProps({
  project: {
    type: Object,
    required: true,
  },
})

function formatDate(iso) {
  return new Date(iso).toLocaleDateString()
}
</script>

<template>
  <RouterLink :to="`/projects/${project.project_id}`" class="project-card card">
    <div class="card-body">
      <img
        v-if="project.metadata?.thumbnail"
        :src="project.metadata.thumbnail"
        :alt="project.metadata?.title"
        class="thumbnail"
      />
      <div class="info">
        <h3>{{ project.metadata?.title ?? 'Untitled' }}</h3>
        <p v-if="project.metadata?.uploader" class="muted">{{ project.metadata.uploader }}</p>
        <p v-if="project.metadata?.duration" class="muted">
          {{ project.metadata.duration }}s
        </p>
        <p class="muted small">{{ formatDate(project.created_at) }}</p>
      </div>
    </div>
    <div class="view-link">View →</div>
  </RouterLink>
</template>

<style scoped lang="scss">@use '../assets/scss/components/ProjectCard';</style>
