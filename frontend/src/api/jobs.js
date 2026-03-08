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

export function getJobStatus(taskId) {
  return client.get(`/jobs/${taskId}/status`)
}

export function getProgressWsUrl(taskId) {
  const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/^http/, 'ws')
  return `${base}/jobs/${taskId}/progress`
}
