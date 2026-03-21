<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useToast } from '@/composables/useToast'
import DropZone from '@/components/DropZone.vue'
import SkeletonBlock from '@/components/SkeletonBlock.vue'

const router = useRouter()
const store = useProjectsStore()
const toast = useToast()
const showCreate = ref(false)

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
    showCreate.value = false
    router.push({ name: 'project-detail', params: { id: project.project_id } })
  } catch {
    toast.error('Failed to create project')
  }
}

function formatDate(d) {
  const date = new Date(d)
  const now = new Date()
  const diffMs = now - date
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

<template>
  <div class="view">
    <!-- Page header -->
    <div class="page-header">
      <h1 class="page-title">Projects</h1>
      <button class="btn btn-primary" @click="showCreate = !showCreate">
        + New Project
      </button>
    </div>

    <!-- Create panel -->
    <div v-if="showCreate" class="create-panel">
      <DropZone @youtube-url="onYoutubeUrl" />
    </div>

    <!-- Recent projects -->
    <section class="section">
      <div class="section-header">
        <span class="section-title">Recent Projects</span>
      </div>

      <!-- Skeleton loading -->
      <template v-if="store.loading">
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Created at</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="n in 4" :key="n" class="skeleton-row">
                <td><SkeletonBlock width="260px" height="13px" /></td>
                <td><SkeletonBlock width="80px" height="13px" /></td>
                <td></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- Empty state -->
      <div v-else-if="!store.projects.length" class="empty">
        <p>No projects yet</p>
        <p class="empty-hint">Paste a YouTube URL above to get started.</p>
      </div>

      <!-- Table -->
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Created at</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="p in store.projects"
              :key="p.project_id"
              class="table-row"
              @click="router.push({ name: 'project-detail', params: { id: p.project_id } })"
            >
              <td class="col-name">
                <div class="project-thumb">
                  <img v-if="p.metadata?.thumbnail" :src="p.metadata.thumbnail" class="thumb-img" alt="" />
                  <div v-else class="thumb-fallback">▶</div>
                </div>
                <span class="project-name">{{ p.metadata?.title || 'Untitled project' }}</span>
              </td>
              <td class="col-date">{{ formatDate(p.created_at) }}</td>
              <td class="col-actions">
                <button
                  class="action-btn"
                  title="Delete"
                  @click.stop="onDeleteProject($event, p.project_id)"
                >···</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.view {
  padding: 40px 48px;
  max-width: 960px;
}

/* ---- Page Header ---- */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
}
.page-title {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.03em;
}

/* ---- Create Panel ---- */
.create-panel {
  margin-bottom: 36px;
  padding: 24px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface-subtle);
}

/* ---- Section ---- */
.section { margin-top: 8px; }

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.section-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-muted);
}

/* ---- Table ---- */
.table-wrap {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table thead tr {
  border-bottom: 1px solid var(--border);
}

.table th {
  padding: 10px 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  background: var(--surface-subtle);
  white-space: nowrap;
}

.table-row {
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  transition: background 0.1s;
}
.table-row:last-child { border-bottom: none; }
.table-row:hover { background: var(--surface-subtle); }

.skeleton-row td { padding: 14px 16px; }

.col-name {
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.col-date {
  padding: 12px 16px;
  font-size: 13px;
  color: var(--text-muted);
  white-space: nowrap;
}

.col-actions {
  padding: 12px 16px;
  text-align: right;
  width: 40px;
}

.project-thumb {
  width: 40px;
  height: 28px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--surface-subtle);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.thumb-fallback {
  font-size: 12px;
  color: var(--text-placeholder);
}

.project-name {
  font-size: 13.5px;
  font-weight: 500;
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 500px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  font-size: 15px;
  color: var(--text-muted);
  background: transparent;
  border: none;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.1s, background 0.1s;
  letter-spacing: 1px;
}
.table-row:hover .action-btn { opacity: 1; }
.action-btn:hover { background: var(--border); color: var(--text); }

/* ---- Empty ---- */
.empty {
  padding: 56px 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 14px;
}
.empty-hint {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-placeholder);
}
</style>
