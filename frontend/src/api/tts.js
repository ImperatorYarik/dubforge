import client from './client'

export function getVoices() {
  return client.get('/tts/voices')
}

export function generateTts(text, speaker, format) {
  return client.post('/tts/generate', { text, speaker, format })
}

export function getTtsStatus(taskId) {
  return client.get(`/tts/${taskId}/status`)
}
