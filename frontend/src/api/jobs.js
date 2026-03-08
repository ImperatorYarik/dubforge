import client from './client'

export function transcribeVideo(projectId, videoId) {
  return client.post('/jobs/transcribe', null, {
    params: { project_id: projectId, video_id: videoId },
  })
}
