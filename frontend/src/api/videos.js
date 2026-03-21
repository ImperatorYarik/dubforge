import client from './client'

export function listVideos() {
  return client.get('/videos/list_videos')
}

export function getVideo(videoId) {
  return client.get(`/videos/${videoId}`)
}

export function uploadVideo(file, projectId) {
  const form = new FormData()
  form.append('file', file)
  return client.post('/videos/upload', form, {
    params: { project_id: projectId },
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getStreamUrl(videoId) {
  return client.get(`/videos/${videoId}/stream`)
}

export function getDubbedStreamUrl(videoId) {
  return client.get(`/videos/${videoId}/dubbed-stream`)
}
