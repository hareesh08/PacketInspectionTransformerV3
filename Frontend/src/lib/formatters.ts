import { format, formatDistanceToNow } from 'date-fns';
import { RiskLevel } from '@/types';

export function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export function formatDate(date: string | Date): string {
  return format(new Date(date), 'yyyy-MM-dd HH:mm:ss');
}

export function formatRelativeTime(date: string | Date): string {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}

export function formatPercentage(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(2)}min`;
}

export function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  
  if (days > 0) return `${days}d ${hours}h ${mins}m`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

export function getRiskColorClass(level: RiskLevel): string {
  const classes: Record<RiskLevel, string> = {
    [RiskLevel.BENIGN]: 'risk-benign',
    [RiskLevel.LOW]: 'risk-low',
    [RiskLevel.MEDIUM]: 'risk-medium',
    [RiskLevel.HIGH]: 'risk-high',
    [RiskLevel.CRITICAL]: 'risk-critical',
  };
  return classes[level];
}

export function getRiskTextColor(level: RiskLevel): string {
  const colors: Record<RiskLevel, string> = {
    [RiskLevel.BENIGN]: 'text-risk-benign',
    [RiskLevel.LOW]: 'text-risk-low',
    [RiskLevel.MEDIUM]: 'text-risk-medium',
    [RiskLevel.HIGH]: 'text-risk-high',
    [RiskLevel.CRITICAL]: 'text-risk-critical',
  };
  return colors[level];
}
