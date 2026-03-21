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

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('mediaforge_token')
      localStorage.removeItem('mediaforge_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
