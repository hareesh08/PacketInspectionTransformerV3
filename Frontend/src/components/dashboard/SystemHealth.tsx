import { Database, Cpu, Clock, HardDrive } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatUptime, formatBytes } from '@/lib/formatters';
import { HealthStatus } from '@/types';

interface SystemHealthProps {
  health: HealthStatus | null;
}

export function SystemHealth({ health }: SystemHealthProps) {
  // Handle case when health data is not available
  if (!health) {
    return (
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-foreground">System Health</h3>
            <p className="text-sm text-muted-foreground">Real-time infrastructure status</p>
          </div>
          <div className="flex items-center gap-2 rounded-full px-3 py-1 bg-risk-medium/10">
            <span className="h-2 w-2 rounded-full bg-risk-medium animate-pulse" />
            <span className="text-sm font-medium text-risk-medium">Unknown</span>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                <Cpu className="h-4 w-4 text-primary" />
              </div>
              <div>
                <div className="text-sm font-medium text-foreground">ML Model</div>
                <div className="text-xs text-muted-foreground">Waiting for data...</div>
              </div>
            </div>
          </div>
          <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                <Database className="h-4 w-4 text-primary" />
              </div>
              <div>
                <div className="text-sm font-medium text-foreground">Database</div>
                <div className="text-xs text-muted-foreground">Waiting for data...</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const statusColors = {
    healthy: 'text-risk-benign',
    degraded: 'text-risk-medium',
    unhealthy: 'text-risk-critical',
  };

  const statusBg = {
    healthy: 'bg-risk-benign/10',
    degraded: 'bg-risk-medium/10',
    unhealthy: 'bg-risk-critical/10',
  };

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-foreground">System Health</h3>
          <p className="text-sm text-muted-foreground">Real-time infrastructure status</p>
        </div>
        <div
          className={cn(
            'flex items-center gap-2 rounded-full px-3 py-1',
            statusBg[health.status]
          )}
        >
          <span
            className={cn(
              'h-2 w-2 rounded-full animate-pulse',
              health.status === 'healthy' && 'bg-risk-benign',
              health.status === 'degraded' && 'bg-risk-medium',
              health.status === 'unhealthy' && 'bg-risk-critical'
            )}
          />
          <span className={cn('text-sm font-medium capitalize', statusColors[health.status])}>
            {health.status}
          </span>
        </div>
      </div>

      <div className="space-y-4">
        {/* Model Status */}
        <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <Cpu className="h-4 w-4 text-primary" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">ML Model</div>
              <div className="text-xs text-muted-foreground">{health.model.device}</div>
            </div>
          </div>
          <div className="text-right">
            <div className={cn('text-sm font-medium', health.model.loaded ? 'text-risk-benign' : 'text-risk-critical')}>
              {health.model.loaded ? 'Loaded' : 'Not Loaded'}
            </div>
            <div className="text-xs text-muted-foreground">
              {health.model.num_layers} layers
            </div>
          </div>
        </div>

        {/* Database Status */}
        <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <Database className="h-4 w-4 text-primary" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">Database</div>
              <div className="text-xs text-muted-foreground truncate max-w-[140px]">
                {health.database.path}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className={cn('text-sm font-medium', health.database.connected ? 'text-risk-benign' : 'text-risk-critical')}>
              {health.database.connected ? 'Connected' : 'Disconnected'}
            </div>
            <div className="text-xs text-muted-foreground">
              {health.database.total_threats.toLocaleString()} threats
            </div>
          </div>
        </div>

        {/* Uptime & Memory */}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex items-center gap-3 rounded-lg bg-secondary/50 px-4 py-3">
            <Clock className="h-4 w-4 text-primary" />
            <div>
              <div className="text-xs text-muted-foreground">Uptime</div>
              <div className="text-sm font-medium text-foreground">
                {formatUptime(health.uptime_seconds)}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-lg bg-secondary/50 px-4 py-3">
            <HardDrive className="h-4 w-4 text-primary" />
            <div>
              <div className="text-xs text-muted-foreground">Memory</div>
              <div className="text-sm font-medium text-foreground">
                {formatBytes(health.memory_usage_mb * 1024 * 1024)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
