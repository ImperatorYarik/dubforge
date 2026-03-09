import client from './client'

export function createProject(youtubeUrl, downloadFromYoutube = true) {
  return client.post('/projects/create', null, {
    params: { youtube_url: youtubeUrl, download_from_youtube: downloadFromYoutube },
  })
}

export function listProjects() {
  return client.get('/projects/list_projects')
}

export function getProject(projectId) {
  return client.get(`/projects/${projectId}`)
}

export function deleteProject(projectId) {
  return client.delete(`/projects/${projectId}`)
}
