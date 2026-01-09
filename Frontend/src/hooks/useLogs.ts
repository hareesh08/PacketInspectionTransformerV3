import { useEffect, useState, useCallback, useRef } from 'react';
import { LogEntry, LogFilter, LogLevel } from '@/types';
import { api } from '@/lib/api';

interface UseLogsOptions {
  enabled?: boolean;
  maxLogs?: number;
  initialFilter?: LogFilter;
}

export function useLogs({
  enabled = true,
  maxLogs = 500,
  initialFilter,
}: UseLogsOptions = {}) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [filter, setFilter] = useState<LogFilter>(initialFilter || { source: 'all' });
  const eventSourceRef = useRef<EventSource | null>(null);

  // Add a log entry
  const addLog = useCallback(async (level: LogLevel, message: string) => {
    try {
      await api.sendFrontendLog(level, message);
    } catch (error) {
      console.error('Failed to send frontend log:', error);
    }
  }, []);

  // Clear all logs
  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  // Handle incoming log
  const handleLog = useCallback((log: LogEntry) => {
    setLogs((prev) => [log, ...prev].slice(0, maxLogs));
  }, [maxLogs]);

  // Handle errors
  const handleError = useCallback((error: Event) => {
    console.error('Log stream error:', error);
    setIsConnected(false);
  }, []);

  // Load initial logs
  const loadLogs = useCallback(async () => {
    try {
      const response = await api.getLogs();
      setLogs(response.logs);
    } catch (error) {
      console.error('Failed to load logs:', error);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;

    // Load initial logs
    loadLogs();

    // Connect to log stream
    const eventSource = api.connectLogsStream(handleLog, handleError);
    eventSourceRef.current = eventSource;
    setIsConnected(true);

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    };
  }, [enabled, handleLog, handleError, loadLogs]);

  // Filter logs based on current filter
  const filteredLogs = logs.filter((log) => {
    if (filter.level && log.level !== filter.level) {
      return false;
    }
    if (filter.source && filter.source !== 'all' && log.source !== filter.source) {
      return false;
    }
    if (filter.search) {
      const searchLower = filter.search.toLowerCase();
      return (
        log.message.toLowerCase().includes(searchLower) ||
        log.level.toLowerCase().includes(searchLower) ||
        log.source.toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  return {
    logs: filteredLogs,
    allLogs: logs,
    isConnected,
    filter,
    setFilter,
    addLog,
    clearLogs,
    loadLogs,
    logCount: filteredLogs.length,
  };
}