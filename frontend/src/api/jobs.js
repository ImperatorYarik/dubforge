import client from './client'

export function transcribeVideo(projectId, videoId, options = {}) {
  const { translate = true, model = 'large-v3', skip_demucs = false, language = null } = options
  const params = { project_id: projectId, video_id: videoId, translate, model, skip_demucs }
  if (language) params.language = language
  return client.post('/jobs/transcribe', null, { params })
}

export function dubVideo(projectId, videoId, options = {}) {
  const {
    skip_transcription = false,
    ducking_enabled = true,
    ducking_level = 0.3,
    atempo_min = 0.75,
    atempo_max = 1.5,
    segments = null,
  } = options
  const body = segments ? { segments } : null
  return client.post('/jobs/dub', body, {
    params: {
      project_id: projectId,
      video_id: videoId,
      skip_transcription,
      ducking_enabled,
      ducking_level,
      atempo_min,
      atempo_max,
    },
  })
}

export function redubVideo(projectId, videoId, options = {}) {
  return dubVideo(projectId, videoId, { ...options, skip_transcription: true })
}

export function separateAudio(projectId, videoId) {
  return client.post('/jobs/separate', null, {
    params: { project_id: projectId, video_id: videoId },
  })
}

export function getJobStatus(taskId) {
  return client.get(`/jobs/${taskId}/status`)
}

export function getRecentJobs(limit = 20) {
  return client.get('/jobs/recent', { params: { limit } })
}

export function getProgressWsUrl(taskId) {
  const apiBase = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL
  if (apiBase) {
    return apiBase.replace(/^http/, 'ws') + `/jobs/${taskId}/progress`
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/jobs/${taskId}/progress`
}
