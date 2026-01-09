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
