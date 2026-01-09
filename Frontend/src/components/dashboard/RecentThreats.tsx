import { AlertTriangle, ExternalLink, FileText, Globe } from 'lucide-react';
import { ThreatLog, RiskLevel, SourceType } from '@/types';
import { formatRelativeTime, getRiskColorClass } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface RecentThreatsProps {
  threats: ThreatLog[];
}

export function RecentThreats({ threats }: RecentThreatsProps) {
  if (threats.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-lg font-semibold text-foreground mb-4">Recent Threats</h3>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-risk-benign/10 mb-3">
            <AlertTriangle className="h-6 w-6 text-risk-benign" />
          </div>
          <p className="text-sm text-muted-foreground">No threats detected recently</p>
          <p className="text-xs text-muted-foreground mt-1">System is operating normally</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-foreground">Recent Threats</h3>
        <a
          href="/threats"
          className="flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
        >
          View all
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>

      <div className="space-y-3">
        {threats.map((threat) => (
          <div
            key={threat.id}
            className={cn(
              'flex items-center gap-4 rounded-lg bg-secondary/50 px-4 py-3 transition-all hover:bg-secondary/70',
              threat.risk_level === RiskLevel.CRITICAL && 'border-l-2 border-risk-critical'
            )}
          >
            {/* Source icon */}
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-background">
              {threat.source_type === SourceType.URL ? (
                <Globe className="h-4 w-4 text-muted-foreground" />
              ) : (
                <FileText className="h-4 w-4 text-muted-foreground" />
              )}
            </div>

            {/* Source info */}
            <div className="min-w-0 flex-1">
              <div className="truncate font-mono text-sm text-foreground">
                {threat.source}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-muted-foreground">
                  {formatRelativeTime(threat.timestamp)}
                </span>
                <span className="text-xs text-muted-foreground">•</span>
                <span className="text-xs text-muted-foreground">
                  {(threat.probability * 100).toFixed(1)}% confidence
                </span>
              </div>
            </div>

            {/* Risk badge */}
            <Badge
              variant="outline"
              className={cn('shrink-0 border', getRiskColorClass(threat.risk_level))}
            >
              {threat.risk_level}
            </Badge>

            {/* Blocked indicator */}
            {threat.blocked && (
              <div className="shrink-0 rounded-full bg-risk-critical/10 px-2 py-1">
                <span className="text-xs font-medium text-risk-critical">BLOCKED</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
