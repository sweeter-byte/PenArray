import axios from 'axios';

/**
 * API Client for BiZhen Backend
 *
 * Provides axios-based HTTP client and native EventSource SSE streaming.
 */

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

/**
 * Authentication API
 */
export const authApi = {
  /**
   * Login with username and password
   */
  login: (username, password) =>
    apiClient.post('/auth/login', { username, password }),

  /**
   * Get current user info
   */
  getMe: () => apiClient.get('/auth/me'),
};

/**
 * Task API
 */
export const taskApi = {
  /**
   * Create a new essay generation task
   */
  create: (prompt, imageUrl = null) =>
    apiClient.post('/task/create', { prompt, image_url: imageUrl }),

  /**
   * Get task result with all essays
   */
  getResult: (taskId) =>
    apiClient.get(`/task/${taskId}/result`),

  /**
   * Get quick task status
   */
  getStatus: (taskId) =>
    apiClient.get(`/task/${taskId}/status`),

  /**
   * Subscribe to task progress via Server-Sent Events (SSE)
   *
   * @param {number} taskId - Task ID to stream
   * @param {Object} callbacks - Event callbacks
   * @param {function} callbacks.onMessage - Called for each progress message
   * @param {function} callbacks.onComplete - Called when task completes
   * @param {function} callbacks.onError - Called on error
   * @returns {function} Cleanup function to close connection
   */
  streamProgress: (taskId, { onMessage, onComplete, onError }) => {
    const url = `/api/task/${taskId}/stream`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'progress') {
          onMessage?.(data);
        } else if (data.type === 'end') {
          onComplete?.(data);
          eventSource.close();
        } else if (data.type === 'error') {
          onError?.(new Error(data.message || 'Task failed'));
          eventSource.close();
        } else if (data.type === 'connected') {
          onMessage?.({ agent: 'system', message: 'Connected...' });
        }
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      onError?.(new Error('Connection lost'));
      eventSource.close();
    };

    // Return cleanup function
    return () => eventSource.close();
  },
};

/**
 * Check if user is authenticated
 */
export const isAuthenticated = () => !!localStorage.getItem('token');

/**
 * Save auth token
 */
export const setToken = (token) => localStorage.setItem('token', token);

/**
 * Remove auth token (logout)
 */
export const clearToken = () => localStorage.removeItem('token');

export default apiClient;
