// Enums
export enum RiskLevel {
  BENIGN = 'BENIGN',
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
}

export enum SourceType {
  URL = 'URL',
  FILE = 'FILE',
}

export enum ScanStatus {
  CLEAN = 'CLEAN',
  THREAT_DETECTED = 'THREAT_DETECTED',
  ERROR = 'ERROR',
  PENDING = 'PENDING',
}

// Response Models
export interface ModelStatus {
  loaded: boolean;
  model_path: string;
  device: string;
  parameters?: number;
  vocab_size: number;
  d_model: number;
  num_layers: number;
}

export interface DatabaseStatus {
  connected: boolean;
  path: string;
  total_threats: number;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  model: ModelStatus;
  database: DatabaseStatus;
  uptime_seconds: number;
  memory_usage_mb: number;
  timestamp: string;
}

export interface ScanResult {
  source: string;
  source_type: SourceType;
  probability: number;
  risk_level: RiskLevel;
  bytes_scanned: number;
  blocked: boolean;
  scan_time_ms: number;
  status: ScanStatus;
  details?: Record<string, unknown>;
  timestamp: string;
}

export interface ThreatLog {
  id: number;
  source: string;
  source_type: SourceType;
  probability: number;
  bytes_scanned: number;
  risk_level: RiskLevel;
  timestamp: string;
  details?: string;
  blocked: boolean;
}

export interface ThreatListResponse {
  threats: ThreatLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface ThreatStats {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  benign: number;
  total_bytes_scanned: number;
}

export interface RiskDistribution {
  BENIGN: number;
  LOW: number;
  MEDIUM: number;
  HIGH: number;
  CRITICAL: number;
}

export interface SettingsStatus {
  confidence_threshold: number;
  chunk_size: number;
  window_size: number;
  temperature: number;
  risk_levels: Record<string, [number, number]>;
}

export interface DetectorStats {
  total_scans: number;
  threats_detected: number;
  bytes_scanned: number;
  avg_scan_time_ms: number;
  last_scan_time?: string;
}

export interface ThreatManagerStats {
  total_threats: number;
  threats_by_level: Record<string, number>;
}

export interface FullStatsResponse {
  detector: DetectorStats;
  threat_manager: ThreatManagerStats;
  uptime_seconds: number;
}

export interface ThresholdResponse {
  old_threshold: number;
  new_threshold: number;
  status: string;
}

// =====================================================================
// Model Info & Resource Monitoring Types
// =====================================================================

export interface GPUInfo {
  available: boolean;
  device_name: string | null;
  device_index: number;
  total_memory_gb: number | null;
  allocated_memory_gb: number | null;
  cached_memory_gb: number | null;
  compute_capability: string | null;
}

export interface CPUInfo {
  logical_cores: number;
  physical_cores: number;
  frequency_mhz: number | null;
  cpu_percent: number;
}

export interface MemoryInfo {
  total_gb: number;
  available_gb: number;
  used_gb: number;
  percent_used: number;
  swap_total_gb: number;
  swap_used_gb: number;
}

export interface ModelInfo {
  loaded: boolean;
  model_path: string;
  total_parameters: number;
  trainable_parameters: number;
  vocab_size: number;
  d_model: number;
  nhead: number;
  num_layers: number;
  dim_feedforward: number;
  dropout: number;
}

export interface ModelInfoResponse {
  device: string;
  device_type: 'GPU' | 'CPU';
  cpu: CPUInfo;
  memory: MemoryInfo;
  gpu: GPUInfo;
  model: ModelInfo;
  uptime_seconds: number;
  timestamp: string;
}

// =====================================================================
// Notification Types
// =====================================================================

export interface Notification {
  id?: string;
  event: string;
  title?: string;
  message?: string;
  timestamp: string;
  data: {
    source?: string;
    source_type?: string;
    probability?: number;
    risk_level?: string;
    bytes_scanned?: number;
    scan_time_ms?: number;
    timestamp?: string;
    message?: string;
    [key: string]: unknown;
  };
}

export type NotificationEvent =
  | 'threat_detected'
  | 'scan_completed'
  | 'model_status'
  | 'system_alert'
  | 'heartbeat'
  | 'test';

// =====================================================================
// Log Types
// =====================================================================

export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  source: 'backend' | 'frontend';
}

export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';

export interface LogFilter {
  level?: LogLevel;
  source?: 'backend' | 'frontend' | 'all';
  search?: string;
}
