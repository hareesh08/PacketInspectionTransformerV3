import { useEffect, useRef, useState } from 'react';
import { LogEntry, LogLevel } from '@/types';
import { useLogs } from '@/hooks/useLogs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Terminal,
  X,
  RotateCcw,
  Trash2,
  Search,
  Filter,
  Pause,
  Play,
} from 'lucide-react';

interface LogViewerProps {
  isOpen: boolean;
  onClose: () => void;
}

const logLevelColors: Record<LogLevel, string> = {
  DEBUG: 'text-gray-400',
  INFO: 'text-blue-400',
  WARNING: 'text-yellow-400',
  ERROR: 'text-red-400',
  CRITICAL: 'text-red-600 font-bold',
};

const logLevelBadges: Record<LogLevel, string> = {
  DEBUG: 'bg-gray-500/20 text-gray-400',
  INFO: 'bg-blue-500/20 text-blue-400',
  WARNING: 'bg-yellow-500/20 text-yellow-400',
  ERROR: 'bg-red-500/20 text-red-400',
  CRITICAL: 'bg-red-600/20 text-red-600',
};

export function LogViewer({ isOpen, onClose }: LogViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [newLogHighlight, setNewLogHighlight] = useState(false);
  const previousLogCountRef = useRef(0);

  const {
    logs,
    isConnected,
    filter,
    setFilter,
    addLog,
    clearLogs,
    loadLogs,
  } = useLogs({ enabled: isOpen, maxLogs: 1000 });

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  // Highlight when new logs arrive
  useEffect(() => {
    if (logs.length > previousLogCountRef.current) {
      setNewLogHighlight(true);
      const timer = setTimeout(() => setNewLogHighlight(false), 500);
      return () => clearTimeout(timer);
    }
    previousLogCountRef.current = logs.length;
  }, [logs.length]);

  // Format timestamp
  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      const timeStr = date.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      const ms = date.getUTCMilliseconds().toString().padStart(3, '0');
      return `${timeStr}.${ms}`;
    } catch {
      return timestamp;
    }
  };

  // Handle manual log submission
  const handleSubmitLog = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const message = formData.get('message') as string;
    const level = (formData.get('level') as LogLevel) || 'INFO';
    if (message.trim()) {
      await addLog(level, message.trim());
      (e.target as HTMLFormElement).reset();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-4xl h-[80vh] bg-background rounded-lg shadow-2xl flex flex-col overflow-hidden border border-border">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-secondary/50">
          <div className="flex items-center gap-3">
            <Terminal className="h-5 w-5 text-foreground" />
            <h2 className="text-lg font-semibold text-foreground">Live Logs</h2>
            <Badge variant="outline" className={isConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </Badge>
            <Badge variant="outline">{logs.length} entries</Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setAutoScroll(!autoScroll)}
              className={autoScroll ? 'text-green-400' : 'text-muted-foreground'}
              title={autoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
            >
              {autoScroll ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon" onClick={loadLogs} title="Reload logs">
              <RotateCcw className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={clearLogs} title="Clear logs">
              <Trash2 className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 px-4 py-2 border-b border-border bg-secondary/30">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search logs..."
              value={filter.search || ''}
              onChange={(e) => setFilter({ ...filter, search: e.target.value })}
              className="pl-9 h-8 bg-background border-border"
            />
          </div>
          <div className="flex items-center gap-1">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select
              value={filter.level || ''}
              onChange={(e) => setFilter({ ...filter, level: e.target.value as LogLevel || undefined })}
              className="h-8 px-2 bg-background border border-border rounded text-sm"
            >
              <option value="">All Levels</option>
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
            <select
              value={filter.source || 'all'}
              onChange={(e) => setFilter({ ...filter, source: e.target.value as 'backend' | 'frontend' | 'all' })}
              className="h-8 px-2 bg-background border border-border rounded text-sm"
            >
              <option value="all">All Sources</option>
              <option value="backend">Backend</option>
              <option value="frontend">Frontend</option>
            </select>
          </div>
        </div>

        {/* Log Display */}
        <div
          ref={scrollRef}
          className={`flex-1 overflow-auto p-4 font-mono text-sm bg-[#0d1117] ${
            newLogHighlight ? 'animate-pulse' : ''
          }`}
          style={{ scrollBehavior: 'smooth' }}
        >
          {logs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <p>No logs yet. Waiting for events...</p>
            </div>
          ) : (
            <div className="space-y-1">
              {logs.map((log, index) => (
                <div
                  key={`${log.timestamp}-${index}`}
                  className="flex items-start gap-2 hover:bg-white/5 rounded px-1"
                >
                  <span className="text-muted-foreground shrink-0 text-xs">
                    {formatTime(log.timestamp)}
                  </span>
                  <Badge
                    variant="secondary"
                    className={`shrink-0 text-xs font-mono ${logLevelBadges[log.level as LogLevel]}`}
                  >
                    {log.level}
                  </Badge>
                  <Badge
                    variant="outline"
                    className={`shrink-0 text-xs ${
                      log.source === 'backend'
                        ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
                        : 'bg-orange-500/20 text-orange-400 border-orange-500/30'
                    }`}
                  >
                    {log.source}
                  </Badge>
                  <span className={`${logLevelColors[log.level as LogLevel] || 'text-foreground'}`}>
                    {log.message}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Log Input */}
        <form onSubmit={handleSubmitLog} className="flex items-center gap-2 px-4 py-3 border-t border-border bg-secondary/30">
          <select
            name="level"
            defaultValue="INFO"
            className="h-8 px-2 bg-background border border-border rounded text-sm"
          >
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>
          <Input
            name="message"
            placeholder="Type a log message..."
            className="flex-1 h-8 bg-background border-border font-mono text-sm"
            autoComplete="off"
          />
          <Button type="submit" size="sm">
            Send
          </Button>
        </form>
      </div>
    </div>
  );
}