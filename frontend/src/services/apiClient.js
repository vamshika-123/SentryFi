import axios from 'axios';

// Base URL falls back to local proxy `/api` if VITE_API_BASE_URL is missing
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds for heavy ML inference operations
  headers: {
    'Content-Type': 'application/json'
  }
});

// Response interceptor for unified error handling and retries
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    // Automatic retry logic for 502/503/504 or network errors on cold starts
    if (!originalRequest._retry && error.response && error.response.status >= 502) {
      originalRequest._retry = true;
      // Wait for 2 seconds before retrying (gives ML models a chance to warm up)
      await new Promise(resolve => setTimeout(resolve, 2000));
      return apiClient(originalRequest);
    }
    
    // Format human-readable error messages
    let errorMessage = "An unexpected error occurred.";
    if (!error.response) {
      errorMessage = "Network Error: Could not reach the ML threat detection engine. Please check your connection.";
    } else if (error.response.data && error.response.data.detail) {
      errorMessage = error.response.data.detail;
    } else {
      errorMessage = `Server Error (${error.response.status}): The ML pipeline encountered an issue.`;
    }
    
    // Attach clean formatted message
    error.message = errorMessage;
    return Promise.reject(error);
  }
);

export default apiClient;
