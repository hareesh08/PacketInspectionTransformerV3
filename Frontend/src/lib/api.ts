/**
 * API Client for Malware Detection Gateway Backend
 * Uses axios for HTTP requests with interceptors for error handling
 */

import axios, { AxiosError, AxiosInstance, AxiosResponse } from 'axios';

// =====================================================================
// Configuration
// =====================================================================

// API Base URL - configurable via environment variable
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Request timeout in milliseconds
const REQUEST_TIMEOUT = 30000;

// =====================================================================
// Type Definitions (matching backend models)
// =====================================================================

// Request types
export interface URLScanRequest {
  url: string;
  block_on_detection?: boolean;
}

export interface ThresholdUpdateRequest {
  threshold: number;
}

export interface ThreatListParams {
  limit?: number;
  offset?: number;
  risk_level?: string;
  source_type?: string;
}

// API Error response (matches backend ErrorResponse model)
export interface ApiErrorResponse {
  error: string;
  message: string;
  details?: Record<string, unknown>;
  timestamp?: string;
}

// =====================================================================
// API Client Class
// =====================================================================

class ApiClient {
  private client: AxiosInstance;

  constructor(baseUrl: string = API_BASE_URL, timeout: number = REQUEST_TIMEOUT) {
    this.client = axios.create({
      baseURL: baseUrl,
      timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // You can add auth tokens here in the future
        // const token = localStorage.getItem('auth_token');
        // if (token) {
        //   config.headers.Authorization = `Bearer ${token}`;
        // }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        return response;
      },
      (error: AxiosError<ApiErrorResponse>) => {
        if (error.response) {
          // Server responded with error
          const errorData = error.response.data;
          const message = errorData?.message || errorData?.error || error.message;
          const status = error.response.status;
          
          const apiError = new ApiError(
            message,
            status,
            errorData?.details
          );
          return Promise.reject(apiError);
        } else if (error.request) {
          // Request was made but no response received
          return Promise.reject(new ApiError('No response from server', 0));
        } else {
          // Something went wrong setting up the request
          return Promise.reject(new ApiError(error.message || 'Unknown error', 0));
        }
      }
    );
  }

  // =====================================================================
  // Health & Settings Endpoints
  // =====================================================================

  /**
   * Get system health status
   */
  async getHealth(): Promise<import('@/types').HealthStatus> {
    const response = await this.client.get('/health');
    return response.data;
  }

  /**
   * Get current settings
   */
  async getSettings(): Promise<import('@/types').SettingsStatus> {
    const response = await this.client.get('/settings');
    return response.data;
  }

  /**
   * Update detection threshold
   */
  async updateThreshold(threshold: number): Promise<{
    old_threshold: number;
    new_threshold: number;
    status: string;
  }> {
    const response = await this.client.post('/settings/threshold', { threshold });
    return response.data;
  }

  // =====================================================================
  // Scanning Endpoints
  // =====================================================================

  /**
   * Scan a URL for malware
   */
  async scanUrl(
    url: string,
    blockOnDetection: boolean = true
  ): Promise<import('@/types').ScanResult> {
    const response = await this.client.post('/scan/url', {
      url,
      block_on_detection: blockOnDetection,
    });
    return response.data;
  }

  /**
   * Scan a file for malware
   */
  async scanFile(
    file: File,
    blockOnDetection: boolean = true
  ): Promise<import('@/types').ScanResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('block_on_detection', String(blockOnDetection));

    const response = await this.client.post('/scan/file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      params: {
        block_on_detection: blockOnDetection,
      },
    });

    return response.data;
  }

  // =====================================================================
  // Threat Management Endpoints
  // =====================================================================

  /**
   * Get threat logs with pagination and filtering
   */
  async getThreats(params?: ThreatListParams): Promise<import('@/types').ThreatListResponse> {
    const response = await this.client.get('/threats', { params });
    return response.data;
  }

  /**
   * Get aggregated threat statistics
   */
  async getThreatStats(): Promise<import('@/types').ThreatStats> {
    const response = await this.client.get('/threats/stats');
    return response.data;
  }

  /**
   * Get threat distribution by risk level
   */
  async getThreatDistribution(): Promise<import('@/types').RiskDistribution> {
    const response = await this.client.get('/threats/distribution');
    return response.data;
  }

  /**
   * Get a specific threat by ID
   */
  async getThreatById(threatId: number): Promise<import('@/types').ThreatLog> {
    const response = await this.client.get(`/threats/${threatId}`);
    return response.data;
  }

  // =====================================================================
  // Statistics Endpoints
  // =====================================================================

  /**
   * Get detector and system statistics
   */
  async getStats(): Promise<import('@/types').FullStatsResponse> {
    const response = await this.client.get('/stats');
    return response.data;
  }
}

// =====================================================================
// Custom Error Class
// =====================================================================

export class ApiError extends Error {
  public status: number;
  public details?: Record<string, unknown>;

  constructor(
    message: string,
    status: number = 500,
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

// =====================================================================
// Export Singleton Instance
// =====================================================================

export const api = new ApiClient();

// Also export individual methods for convenience
export const {
  getHealth,
  getSettings,
  updateThreshold,
  scanUrl,
  scanFile,
  getThreats,
  getThreatStats,
  getThreatDistribution,
  getThreatById,
  getStats,
} = api;

// Export the class for testing or custom instances
export { ApiClient };