import client from './client'

export function listVideos() {
  return client.get('/videos/list_videos')
}

export function getVideo(videoId) {
  return client.get(`/videos/${videoId}`)
}

export function uploadVideo(file, projectId, onProgress) {
  const form = new FormData()
  form.append('file', file)
  return client.post('/videos/upload', form, {
    params: { project_id: projectId },
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
  })
}

export function getStreamUrl(videoId) {
  return client.get(`/videos/${videoId}/stream`)
}

export function getDubbedStreamUrl(videoId) {
  return client.get(`/videos/${videoId}/dubbed-stream`)
}

export function getVocalsStreamUrl(videoId) {
  return client.get(`/videos/${videoId}/vocals-stream`)
}

export function getNoVocalsStreamUrl(videoId) {
  return client.get(`/videos/${videoId}/no-vocals-stream`)
}

export function getDubbedVersionStreamUrl(videoId, jobId) {
  return client.get(`/videos/${videoId}/dubbed-versions/${jobId}/stream`)
}

export function deleteDubbedVersion(videoId, jobId) {
  return client.delete(`/videos/${videoId}/dubbed-versions/${jobId}`)
}
