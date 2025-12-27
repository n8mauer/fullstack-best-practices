/**
 * API Client demonstrating best practices:
 * - Centralized API logic
 * - Type safety
 * - Error handling
 * - Token management
 * - Request/response interceptors
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

// Custom error class for better error handling
export class APIError extends Error {
  constructor(
    public status: number,
    public data: any,
    message?: string
  ) {
    super(message || 'API Error');
    this.name = 'APIError';
  }
}

class APIClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000, // 30 seconds
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Add auth token if available
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }

        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config;

        // Handle 401 Unauthorized - try to refresh token
        if (error.response?.status === 401 && originalRequest) {
          try {
            // Attempt to refresh token
            const newToken = await this.refreshToken();
            if (newToken && originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            // Refresh failed, redirect to login
            this.clearAuth();
            if (typeof window !== 'undefined') {
              window.location.href = '/login';
            }
          }
        }

        // Transform axios error to our custom error
        throw new APIError(
          error.response?.status || 500,
          error.response?.data,
          error.message
        );
      }
    );
  }

  /**
   * Set authentication token
   */
  setToken(token: string) {
    this.accessToken = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token);
    }
  }

  /**
   * Clear authentication
   */
  clearAuth() {
    this.accessToken = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  }

  /**
   * Refresh access token
   */
  private async refreshToken(): Promise<string | null> {
    const refreshToken = typeof window !== 'undefined'
      ? localStorage.getItem('refresh_token')
      : null;

    if (!refreshToken) {
      return null;
    }

    try {
      const response = await this.client.post('/api/v1/auth/token/refresh/', {
        refresh: refreshToken,
      });

      const { access } = response.data;
      this.setToken(access);
      return access;
    } catch (error) {
      return null;
    }
  }

  /**
   * Generic request method
   */
  async request<T>(
    method: string,
    endpoint: string,
    data?: any,
    config?: any
  ): Promise<T> {
    const response = await this.client.request<T>({
      method,
      url: endpoint,
      data,
      ...config,
    });
    return response.data;
  }

  /**
   * GET request
   */
  get<T>(endpoint: string, config?: any): Promise<T> {
    return this.request<T>('GET', endpoint, undefined, config);
  }

  /**
   * POST request
   */
  post<T>(endpoint: string, data?: any, config?: any): Promise<T> {
    return this.request<T>('POST', endpoint, data, config);
  }

  /**
   * PUT request
   */
  put<T>(endpoint: string, data?: any, config?: any): Promise<T> {
    return this.request<T>('PUT', endpoint, data, config);
  }

  /**
   * PATCH request
   */
  patch<T>(endpoint: string, data?: any, config?: any): Promise<T> {
    return this.request<T>('PATCH', endpoint, data, config);
  }

  /**
   * DELETE request
   */
  delete<T>(endpoint: string, config?: any): Promise<T> {
    return this.request<T>('DELETE', endpoint, undefined, config);
  }

  // Authentication methods
  async login(email: string, password: string) {
    const response = await this.post<{ access: string; refresh: string }>(
      '/api/v1/auth/token/',
      { email, password }
    );

    this.setToken(response.access);
    if (typeof window !== 'undefined') {
      localStorage.setItem('refresh_token', response.refresh);
    }

    return response;
  }

  async register(data: {
    email: string;
    username: string;
    password: string;
    password_confirm: string;
    first_name: string;
    last_name: string;
  }) {
    return this.post('/api/v1/users/', data);
  }

  logout() {
    this.clearAuth();
  }

  // Initialize token from storage
  initializeAuth() {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        this.accessToken = token;
      }
    }
  }
}

// Create singleton instance
const apiClient = new APIClient(
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
);

// Initialize auth on client side
if (typeof window !== 'undefined') {
  apiClient.initializeAuth();
}

export default apiClient;
