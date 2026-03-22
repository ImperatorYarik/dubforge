import client from './client'

export function transcribeVideo(projectId, videoId, translate = false) {
  return client.post('/jobs/transcribe', null, {
    params: { project_id: projectId, video_id: videoId, translate },
  })
}

export function dubVideo(projectId, videoId) {
  return client.post('/jobs/dub', null, {
    params: { project_id: projectId, video_id: videoId },
  })
}

export function redubVideo(projectId, videoId) {
  return client.post('/jobs/dub', null, {
    params: { project_id: projectId, video_id: videoId, skip_transcription: true },
  })
}

export function getJobStatus(taskId) {
  return client.get(`/jobs/${taskId}/status`)
}

export function getProgressWsUrl(taskId) {
  const apiBase = import.meta.env.VITE_API_BASE_URL
  if (apiBase) {
    return apiBase.replace(/^http/, 'ws') + `/jobs/${taskId}/progress`
  }
  // Fallback: derive from current page origin
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/jobs/${taskId}/progress`
}
