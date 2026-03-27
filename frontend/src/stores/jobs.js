import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as jobsApi from '@/api/jobs'

const HISTORY_KEY = 'dubforge_job_history'
const MAX_HISTORY = 20

export const useJobsStore = defineStore('jobs', () => {
  const activeJob = ref(null)   // { taskId, type, videoId, projectId }
  const jobHistory = ref(_loadHistory())
  const recentJobs = ref([])
  const loading = ref(false)
  const error = ref(null)
  // LLM translation pipeline phase: null | 'collecting_context' | 'awaiting_review' | 'translating' | 'ready'
  const llmPhase = ref(null)
  let _ws = null

  function _loadHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [] } catch { return [] }
  }

  function _saveHistory() {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(jobHistory.value.slice(0, MAX_HISTORY)))
  }

  function startJob(taskId, type, videoId, projectId) {
    activeJob.value = { taskId, type, videoId, projectId }
    jobHistory.value.unshift({ taskId, type, videoId, projectId, startedAt: Date.now() })
    _saveHistory()
  }

  function disconnectWS() {
    if (_ws) {
      _ws.close()
      _ws = null
    }
  }

  // Open WebSocket to /jobs/{taskId}/progress with reconnect.
  // onMessage({step, pct, message}) called for each event.
  // Returns a Promise that resolves with final progress event (pct>=100) or rejects.
  function connectWS(taskId, onMessage) {
    return new Promise((resolve, reject) => {
      let attempts = 0
      let lastPct = 0

      function connect() {
        const url = jobsApi.getProgressWsUrl(taskId)
        const ws = new WebSocket(url)
        _ws = ws

        ws.onmessage = (e) => {
          const d = JSON.parse(e.data)
          lastPct = d.pct ?? lastPct
          onMessage?.(d)
          if (d.pct >= 100) {
            ws.close()
            resolve(d)
          }
        }

        ws.onerror = () => {
          ws.close()
        }

        ws.onclose = () => {
          if (lastPct >= 100) return
          if (attempts < 3) {
            attempts++
            setTimeout(connect, 2000)
          } else {
            reject(new Error('WebSocket connection lost'))
          }
        }
      }

      connect()
    })
  }

  async function fetchStatus(taskId) {
    const { data } = await jobsApi.getJobStatus(taskId)
    return data
  }

  async function fetchRecentJobs() {
    try {
      const { data } = await jobsApi.getRecentJobs()
      recentJobs.value = data
    } catch {}
  }

  function setLlmPhase(phase) {
    llmPhase.value = phase
  }

  function clearJob() {
    disconnectWS()
    activeJob.value = null
    loading.value = false
    error.value = null
    llmPhase.value = null
  }

  // Legacy helpers used by existing ProjectDetailView
  async function transcribe(projectId, videoId, translate = false, onProgress) {
    loading.value = true
    error.value = null
    try {
      const { data } = await jobsApi.transcribeVideo(projectId, videoId, { translate })
      startJob(data.task_id, 'transcribe', videoId, projectId)
      await connectWS(data.task_id, onProgress)
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function dub(projectId, videoId, options = {}, onProgress) {
    loading.value = true
    error.value = null
    try {
      const { data } = await jobsApi.dubVideo(projectId, videoId, options)
      startJob(data.task_id, 'dub', videoId, projectId)
      await connectWS(data.task_id, onProgress)
      const status = await fetchStatus(data.task_id)
      return status.result
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function redub(projectId, videoId, options = {}, onProgress) {
    return dub(projectId, videoId, { ...options, skip_transcription: true }, onProgress)
  }

  async function separate(projectId, videoId, onProgress) {
    loading.value = true
    error.value = null
    try {
      const { data } = await jobsApi.separateAudio(projectId, videoId)
      startJob(data.task_id, 'separate', videoId, projectId)
      await connectWS(data.task_id, onProgress)
      const status = await fetchStatus(data.task_id)
      return status.result
    } catch (e) {
      error.value = e.response?.data?.detail ?? e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    activeJob,
    jobHistory,
    recentJobs,
    loading,
    error,
    llmPhase,
    startJob,
    setLlmPhase,
    connectWS,
    disconnectWS,
    fetchStatus,
    fetchRecentJobs,
    clearJob,
    transcribe,
    dub,
    redub,
    separate,
  }
})
