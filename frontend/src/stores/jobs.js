import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as jobsApi from '@/api/jobs'

export const useJobsStore = defineStore('jobs', () => {
  const tasks = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Open a WebSocket to /jobs/{taskId}/progress and call onProgress({pct, step, message})
  // on each event. Resolves when pct reaches 100, rejects on error.
  function _watchProgress(taskId, onProgress) {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(jobsApi.getProgressWsUrl(taskId))
      ws.onmessage = (e) => {
        const d = JSON.parse(e.data)
        onProgress?.(d)
        if (d.pct >= 100) {
          ws.close()
          resolve(d)
        }
      }
      ws.onerror = () => {
        ws.close()
        reject(new Error('WebSocket connection failed'))
      }
    })
  }

  // Submit transcription job and track progress via WebSocket.
  // onProgress({ pct, step, message }) is called on each progress event.
  async function transcribe(projectId, videoId, translate = false, onProgress) {
    loading.value = true
    error.value = null
    try {
      const { data } = await jobsApi.transcribeVideo(projectId, videoId, translate)
      await _watchProgress(data.task_id, onProgress)
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  // Submit dub job and track progress via WebSocket.
  // Returns the final Celery result object ({ dubbed_url, transcript_url, ... }).
  async function dub(projectId, videoId, onProgress) {
    loading.value = true
    error.value = null
    try {
      const { data } = await jobsApi.dubVideo(projectId, videoId)
      await _watchProgress(data.task_id, onProgress)
      const { data: s } = await jobsApi.getJobStatus(data.task_id)
      return s.result
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  // Re-dub using existing transcription (skip Whisper).
  async function redub(projectId, videoId, onProgress) {
    loading.value = true
    error.value = null
    try {
      const { data } = await jobsApi.redubVideo(projectId, videoId)
      await _watchProgress(data.task_id, onProgress)
      const { data: s } = await jobsApi.getJobStatus(data.task_id)
      return s.result
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return { tasks, loading, error, transcribe, dub, redub }
})
