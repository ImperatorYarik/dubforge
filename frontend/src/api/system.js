import client from './client'

export function getSystemStatus() {
  return client.get('/system/status')
}
