import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor: add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('mediaforge_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: handle 401 (but don't redirect if already on a page)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Only redirect to login if we're not on setup/login pages
      // and don't redirect for background API calls (settings loading, etc.)
      const path = window.location.pathname
      if (path !== '/login' && path !== '/setup') {
        // Don't auto-redirect - let the component handle the error
        // This prevents settings pages from losing state on transient 401s
      }
    }
    return Promise.reject(error)
  }
)

export default api
