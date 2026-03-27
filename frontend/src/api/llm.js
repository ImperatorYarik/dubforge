import client from './client'

export function getModels() {
  return client.get('/llm/models')
}

export function collectContext(projectId, videoId, model) {
  const params = { project_id: projectId, video_id: videoId }
  if (model) params.model = model
  return client.post('/llm/collect-context', null, { params })
}

export function getContextStatus(taskId) {
  return client.get(`/llm/${taskId}/context-status`)
}

export function translateSegments(payload) {
  return client.post('/llm/translate-segments', payload)
}

export function getTranslateStatus(taskId) {
  return client.get(`/llm/${taskId}/translate-status`)
}
