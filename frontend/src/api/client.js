import axios from 'axios'

/**
 * API Client for BiZhen Backend
 */

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

/**
 * Authentication API
 */
export const authApi = {
  login: (username, password) =>
    apiClient.post('/auth/login', { username, password }),
}

/**
 * Task API
 */
export const taskApi = {
  create: (prompt, imageUrl = null) =>
    apiClient.post('/task/create', { prompt, image_url: imageUrl }),

  getResult: (taskId) =>
    apiClient.get(`/task/${taskId}/result`),

  /**
   * Subscribe to task progress via SSE
   * @param {number} taskId - Task ID
   * @param {function} onMessage - Callback for each message
   * @param {function} onError - Callback for errors
   * @returns {EventSource} - EventSource instance for cleanup
   */
  streamProgress: (taskId, onMessage, onError) => {
    const token = localStorage.getItem('token')
    const url = `/api/task/${taskId}/stream`

    const eventSource = new EventSource(url)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)

        // Close connection on completion or error
        if (data.type === 'end' || data.type === 'error') {
          eventSource.close()
        }
      } catch (e) {
        console.error('Failed to parse SSE message:', e)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE error:', error)
      onError?.(error)
      eventSource.close()
    }

    return eventSource
  },
}

export default apiClient
