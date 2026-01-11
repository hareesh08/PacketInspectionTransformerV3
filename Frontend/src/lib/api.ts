/**
 * API Client for Malware Detection Gateway Backend
 * Uses axios for HTTP requests with interceptors for error handling
 */

import axios, { AxiosError, AxiosInstance, AxiosResponse } from 'axios';
import { ModelInfoResponse, Notification, LogEntry } from '@/types';

// Environment detection
const isProduction = import.meta.env.PROD;
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

// Auto-detect API base URL based on current environment
function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_URL;
  
  // If explicitly set to a full URL, use it
  if (envUrl && (envUrl.startsWith('http://') || envUrl.startsWith('https://'))) {
    return envUrl;
  }
  
  // Auto-detection logic for localhost and production
  if (isLocalhost || !isProduction) {
    // Local development: use localhost with configured port
    const port = import.meta.env.VITE_API_PORT || '8000';
    return `http://localhost:${port}`;
  }
  
  // Production with nginx proxy: use relative URLs
  return '/api';
}

// Get SSE URL for Server-Sent Events connections (uses HTTP/HTTPS, not WebSocket)
function getSSEUrl(): string {
  // For SSE, we use HTTP/HTTPS protocol, not WebSocket
  const apiUrl = getApiBaseUrl();
  
  // If using relative URLs (nginx proxy), return empty base (paths start with /api/)
  if (apiUrl.startsWith('/')) {
    return '';  // Empty base for relative URLs
  }
  
  // For absolute URLs (localhost), return the base URL without /api
  return apiUrl;
}

// API Base URL - configurable via environment variable
const API_BASE_URL = getApiBaseUrl();
const SSE_BASE_URL = getSSEUrl();

// Request timeout in milliseconds (increased for large file scans)
const REQUEST_TIMEOUT = 300000; // 5 minutes

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

export interface EarlyTerminationSettings {
  enabled: boolean;
  threshold: number;
  min_bytes: number;
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
    blockOnDetection: boolean = true,
    earlyTermination: boolean = false
  ): Promise<import('@/types').ScanResult> {
    const response = await this.client.post('/scan/url', {
      url,
      block_on_detection: blockOnDetection,
    }, {
      params: {
        early_termination: earlyTermination,
      },
    });
    return response.data;
  }

  /**
   * Scan a file for malware
   */
  async scanFile(
    file: File,
    blockOnDetection: boolean = true,
    earlyTermination: boolean = false
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
        early_termination: earlyTermination,
      },
    });

    return response.data;
  }

  // =====================================================================
  // Early Termination Settings Endpoints
  // =====================================================================

  /**
   * Get early termination settings
   */
  async getEarlyTerminationSettings(): Promise<EarlyTerminationSettings> {
    const response = await this.client.get('/settings/early-termination');
    return response.data;
  }

  /**
   * Update early termination settings
   */
  async updateEarlyTerminationSettings(
    settings: EarlyTerminationSettings
  ): Promise<{
    old_settings: EarlyTerminationSettings;
    new_settings: EarlyTerminationSettings;
    status: string;
  }> {
    const response = await this.client.post('/settings/early-termination', settings);
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

  // =====================================================================
  // Model Info & Resource Monitoring Endpoints
  // =====================================================================

  /**
   * Get detailed model information including device, cores, and memory
   */
  async getModelInfo(): Promise<ModelInfoResponse> {
    const response = await this.client.get('/model-info');
    return response.data;
  }

  /**
   * Send a test notification
   */
  async sendTestNotification(): Promise<{ status: string }> {
    const response = await this.client.post('/notifications/test');
    return response.data;
  }

  // =====================================================================
  // Server-Sent Events (SSE) for Notifications
  // =====================================================================

  /**
   * Connect to the notifications stream
   */
  connectNotifications(
    onMessage: (notification: Notification) => void,
    onError?: (error: Event) => void
  ): EventSource {
    // Use /api prefix only for nginx proxy (relative URLs), direct for localhost
    const notificationsPath = SSE_BASE_URL ? '/notifications/stream' : '/api/notifications/stream';
    const eventSource = new EventSource(`${SSE_BASE_URL}${notificationsPath}`);
    
    eventSource.onmessage = (event) => {
      try {
        const parsedData = JSON.parse(event.data);
        // Add timestamp if not present (backend may not send it)
        const notification: Notification = {
          ...parsedData,
          timestamp: parsedData.timestamp || new Date().toISOString(),
        };
        onMessage(notification);
      } catch {
        onMessage({
          id: `local-${Date.now()}`,
          event: event.type,
          timestamp: new Date().toISOString(),
          data: JSON.parse(event.data || '{}'),
        });
      }
    };
    
    if (onError) {
      eventSource.onerror = onError;
    }
    
    return eventSource;
  }

  // =====================================================================
  // Log Streaming Endpoints
  // =====================================================================

  /**
   * Get recent log entries (non-streaming)
   */
  async getLogs(): Promise<{ logs: LogEntry[]; total: number }> {
    const response = await this.client.get('/logs');
    return response.data;
  }

  /**
   * Send a test log entry
   */
  async sendTestLog(): Promise<{ status: string }> {
    const response = await this.client.post('/logs/test');
    return response.data;
  }

  /**
   * Send a log entry from the frontend
   */
  async sendFrontendLog(level: string, message: string): Promise<{ status: string }> {
    const response = await this.client.post('/logs/frontend', { level, message });
    return response.data;
  }

  /**
   * Connect to the logs stream (SSE)
   */
  connectLogsStream(
    onLog: (log: LogEntry) => void,
    onError?: (error: Event) => void
  ): EventSource {
    // Use /api prefix only for nginx proxy (relative URLs), direct for localhost
    const logsPath = SSE_BASE_URL ? '/logs/stream' : '/api/logs/stream';
    const eventSource = new EventSource(`${SSE_BASE_URL}${logsPath}`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'log') {
          onLog(data.data as LogEntry);
        }
      } catch (error) {
        console.error('Failed to parse log entry:', error);
      }
    };
    
    if (onError) {
      eventSource.onerror = onError;
    }
    
    return eventSource;
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
  getModelInfo,
  sendTestNotification,
  connectNotifications,
  getLogs,
  sendTestLog,
  sendFrontendLog,
  connectLogsStream,
} = api;

// Export the class for testing or custom instances
export { ApiClient };