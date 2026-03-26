import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as projectsApi from '@/api/projects'

const STORAGE_KEY = 'dubforge_current_project_id'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref([])
  const currentProjectId = ref(localStorage.getItem(STORAGE_KEY) || null)
  const loading = ref(false)
  const error = ref(null)

  const currentProject = computed(() =>
    projects.value.find(p => p.project_id === currentProjectId.value) || null
  )

  async function fetchProjects() {
    loading.value = true
    error.value = null
    try {
      const { data } = await projectsApi.listProjects()
      projects.value = data.projects
      // If stored project no longer exists, clear it
      if (currentProjectId.value && !projects.value.find(p => p.project_id === currentProjectId.value)) {
        setCurrentProject(null)
      }
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(projectId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await projectsApi.getProject(projectId)
      // Update in list if present
      const idx = projects.value.findIndex(p => p.project_id === projectId)
      if (idx >= 0) projects.value[idx] = data
      else projects.value.push(data)
      return data
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
    } finally {
      loading.value = false
    }
  }

  function setCurrentProject(id) {
    currentProjectId.value = id
    if (id) {
      localStorage.setItem(STORAGE_KEY, id)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  async function createProject(youtubeUrl, downloadFromYoutube) {
    loading.value = true
    error.value = null
    try {
      const { data } = await projectsApi.createProject(youtubeUrl, downloadFromYoutube)
      await fetchProjects()
      setCurrentProject(data.project_id)
      return data
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createBlankProject(title) {
    error.value = null
    try {
      const { data } = await projectsApi.createBlankProject(title)
      await fetchProjects()
      setCurrentProject(data.project_id)
      return data
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
      throw e
    }
  }

  async function deleteProject(projectId) {
    error.value = null
    try {
      await projectsApi.deleteProject(projectId)
      projects.value = projects.value.filter(p => p.project_id !== projectId)
      if (currentProjectId.value === projectId) {
        setCurrentProject(null)
      }
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
      throw e
    }
  }

  return {
    projects,
    currentProjectId,
    currentProject,
    loading,
    error,
    fetchProjects,
    fetchProject,
    setCurrentProject,
    createProject,
    createBlankProject,
    deleteProject,
  }
})
