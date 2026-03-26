import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 120_000,
})

// Attach X-Project-Id header if a project is active
client.interceptors.request.use((config) => {
  try {
    const id = localStorage.getItem('dubforge_current_project_id')
    if (id) config.headers['X-Project-Id'] = id
  } catch {}
  return config
})

// Global error handling
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response) {
      const msg = err.response.data?.detail || 'API error'
      // Dynamically import toast to avoid circular deps
      import('@/composables/useToast').then(({ useToast }) => {
        useToast().error(msg)
      })
    }
    return Promise.reject(err)
  }
)

export default client
