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

<style scoped lang="scss">
.project-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  text-decoration: none;
  color: var(--color-text);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.project-card:hover {
  border-color: var(--color-accent);
  box-shadow: 0 4px 20px rgb(99, 102, 241, 0.12);
}

.card-body {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.thumbnail {
  width: 100px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
}

.info {
  flex: 1;
  min-width: 0;
}

h3 {
  margin: 0 0 0.3rem;
  font-size: 1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.small {
  font-size: 0.78rem;
}

.view-link {
  margin-top: 0.75rem;
  font-size: 0.85rem;
  color: var(--color-accent);
  font-weight: 500;
}
</style>
