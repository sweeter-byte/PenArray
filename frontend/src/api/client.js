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
  create: (prompt, imageUrl = null, customStructure = null) =>
    apiClient.post('/task/create', {
      prompt,
      image_url: imageUrl,
      custom_structure: customStructure,
    }),

  /**
   * Upload image file and get OCR text
   */
  upload: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/upload/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

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
    const token = localStorage.getItem('token');
    const url = token
      ? `/api/task/${taskId}/stream?token=${encodeURIComponent(token)}`
      : `/api/task/${taskId}/stream`;
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
 * Export API
 */
export const exportApi = {
  /**
   * Download essay as Word document
   */
  downloadDocx: (essayId) => {
    const token = localStorage.getItem('token');
    const url = `/api/export/${essayId}/docx`;
    return downloadFile(url, token);
  },

  /**
   * Download essay as PDF document
   */
  downloadPdf: (essayId) => {
    const token = localStorage.getItem('token');
    const url = `/api/export/${essayId}/pdf`;
    return downloadFile(url, token);
  },
};

/**
 * Helper function to download file with authentication
 */
async function downloadFile(url, token) {
  // Use direct download via URL query param to avoid blob/CORS issues
  const downloadUrl = url.includes('?')
    ? `${url}&token=${encodeURIComponent(token)}`
    : `${url}?token=${encodeURIComponent(token)}`;

  console.log('Starting direct download:', downloadUrl);

  const link = document.createElement('a');
  link.href = downloadUrl;
  link.setAttribute('download', ''); // Hint to browser
  link.style.display = 'none'; // Ensure hidden
  document.body.appendChild(link);

  // Some browsers need a microtask delay
  setTimeout(() => {
    link.click();
    document.body.removeChild(link);
  }, 100);
}

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
