<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useToast } from '@/composables/useToast'
import DropZone from '@/components/DropZone.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'

const router = useRouter()
const store = useProjectsStore()
const toast = useToast()

async function onDeleteProject(event, projectId) {
  event.preventDefault()
  if (!confirm('Delete this project? This cannot be undone.')) return
  try {
    await store.deleteProject(projectId)
    toast.success('Project deleted')
  } catch {
    toast.error('Failed to delete project')
  }
}

onMounted(() => store.fetchProjects())

async function onYoutubeUrl(url) {
  try {
    const project = await store.createProject(url, true)
    toast.success('Project created')
    router.push({ name: 'project-detail', params: { id: project.project_id } })
  } catch {
    toast.error('Failed to create project')
  }
}

function formatDate(d) {
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

<template>
  <div class="view">
    <div class="page-header">
      <h1 class="page-title">Projects</h1>
    </div>

    <div class="hero">
      <DropZone @youtube-url="onYoutubeUrl" />
    </div>

    <section class="section">
      <h2 class="section-title">Recent</h2>

      <div v-if="store.loading" class="grid">
        <div v-for="n in 4" :key="n" class="proj-card skeleton-card">
          <SkeletonBlock width="100%" height="140px" radius="var(--radius)" />
          <div class="card-body">
            <SkeletonBlock width="70%" height="14px" />
            <SkeletonBlock width="40%" height="12px" style="margin-top:6px" />
          </div>
        </div>
      </div>

      <div v-else-if="!store.projects.length" class="empty">
        No projects yet — paste a YouTube URL above to get started.
      </div>

      <div v-else class="grid">
        <div v-for="p in store.projects" :key="p.project_id" class="proj-card-wrap">
          <RouterLink
            :to="{ name: 'project-detail', params: { id: p.project_id } }"
            class="proj-card"
          >
            <div class="thumb-wrap">
              <img v-if="p.metadata?.thumbnail" :src="p.metadata.thumbnail" class="thumb" alt="" />
              <div v-else class="thumb-placeholder">▶</div>
            </div>
            <div class="card-body">
              <p class="card-title">{{ p.metadata?.title || 'Untitled project' }}</p>
              <p class="card-meta">{{ formatDate(p.created_at) }}</p>
            </div>
          </RouterLink>
          <button class="delete-btn" title="Delete project" @click="onDeleteProject($event, p.project_id)">✕</button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.view { padding: 40px 48px; max-width: 960px; }

.page-header { margin-bottom: 28px; }
.page-title { font-size: 20px; font-weight: 600; letter-spacing: -0.025em; }

.hero { margin-bottom: 48px; }

.section-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.proj-card-wrap {
  position: relative;
}
.proj-card-wrap:hover .delete-btn {
  opacity: 1;
}

.delete-btn {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 11px;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}
.delete-btn:hover {
  background: #ef4444;
}

.proj-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--surface);
  transition: box-shadow 0.15s, transform 0.15s;
  cursor: pointer;
}
.proj-card:hover { box-shadow: var(--shadow); transform: translateY(-1px); }
.skeleton-card { cursor: default; }
.skeleton-card:hover { box-shadow: none; transform: none; }

.thumb-wrap { width: 100%; aspect-ratio: 16/9; background: var(--surface-subtle); overflow: hidden; }
.thumb { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumb-placeholder {
  display: flex; align-items: center; justify-content: center;
  height: 100%; font-size: 22px; color: var(--text-placeholder);
}

.card-body { padding: 14px 16px; }
.card-title {
  font-size: 13.5px; font-weight: 500; letter-spacing: -0.01em;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.card-meta { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

.empty { padding: 40px 0; color: var(--text-muted); font-size: 13.5px; }
</style>
