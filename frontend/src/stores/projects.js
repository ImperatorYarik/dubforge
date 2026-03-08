import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as projectsApi from '@/api/projects'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref([])
  const currentProject = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchProjects() {
    loading.value = true
    error.value = null
    try {
      const { data } = await projectsApi.listProjects()
      projects.value = data.projects
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
      currentProject.value = data
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
    } finally {
      loading.value = false
    }
  }

  async function createProject(youtubeUrl, downloadFromYoutube) {
    loading.value = true
    error.value = null
    try {
      const { data } = await projectsApi.createProject(youtubeUrl, downloadFromYoutube)
      await fetchProjects()
      return data
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return { projects, currentProject, loading, error, fetchProjects, fetchProject, createProject }
})
