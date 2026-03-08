import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as jobsApi from '@/api/jobs'

export const useJobsStore = defineStore('jobs', () => {
  const tasks = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function transcribe(projectId, videoId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await jobsApi.transcribeVideo(projectId, videoId)
      tasks.value.push(data)
      return data
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return { tasks, loading, error, transcribe }
})
