import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as videosApi from '@/api/videos'

export const useVideosStore = defineStore('videos', () => {
  const videos = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchVideos() {
    loading.value = true
    error.value = null
    try {
      const { data } = await videosApi.listVideos()
      videos.value = data
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
    } finally {
      loading.value = false
    }
  }

  async function uploadVideo(file, projectId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await videosApi.uploadVideo(file, projectId)
      await fetchVideos()
      return data
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  function videosForProject(projectId) {
    return videos.value.filter((v) => v.project_id === projectId)
  }

  return { videos, loading, error, fetchVideos, uploadVideo, videosForProject }
})
