import { CheckCircle, XCircle, AlertTriangle, Shield, Clock, HardDrive, Percent } from 'lucide-react';
import { ScanResult as ScanResultType, RiskLevel, ScanStatus } from '@/types';
import { formatBytes, formatDuration, getRiskColorClass, getRiskTextColor } from '@/lib/formatters';
import { cn } from '@/lib/utils';

interface ScanResultProps {
  result: ScanResultType;
}

export function ScanResult({ result }: ScanResultProps) {
  const isThreat = result.status === ScanStatus.THREAT_DETECTED;
  const isCritical = result.risk_level === RiskLevel.CRITICAL || result.risk_level === RiskLevel.HIGH;

  return (
    <div
      className={cn(
        'rounded-xl border bg-card p-6 animate-fade-in',
        isThreat ? 'border-risk-critical/50' : 'border-risk-benign/50'
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-4 mb-6">
        <div
          className={cn(
            'flex h-14 w-14 shrink-0 items-center justify-center rounded-xl',
            isThreat ? 'bg-risk-critical/10' : 'bg-risk-benign/10',
            isCritical && 'animate-pulse'
          )}
        >
          {isThreat ? (
            <XCircle className="h-8 w-8 text-risk-critical" />
          ) : (
            <CheckCircle className="h-8 w-8 text-risk-benign" />
          )}
        </div>

        <div className="flex-1">
          <h3 className="text-xl font-bold text-foreground">
            {isThreat ? 'Threat Detected!' : 'Scan Complete - Clean'}
          </h3>
          <p className="text-sm text-muted-foreground mt-1 font-mono truncate">
            {result.source}
          </p>
        </div>

        {/* Risk level badge */}
        <div
          className={cn(
            'flex items-center gap-2 rounded-full border px-4 py-2',
            getRiskColorClass(result.risk_level)
          )}
        >
          <Shield className="h-4 w-4" />
          <span className="font-semibold">{result.risk_level}</span>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="rounded-lg bg-secondary/50 p-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <Percent className="h-4 w-4" />
            <span className="text-xs">Confidence</span>
          </div>
          <div className={cn('text-2xl font-bold', getRiskTextColor(result.risk_level))}>
            {(result.probability * 100).toFixed(1)}%
          </div>
        </div>

        <div className="rounded-lg bg-secondary/50 p-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <HardDrive className="h-4 w-4" />
            <span className="text-xs">Bytes Scanned</span>
          </div>
          <div className="text-2xl font-bold text-foreground">
            {formatBytes(result.bytes_scanned)}
          </div>
        </div>

        <div className="rounded-lg bg-secondary/50 p-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <Clock className="h-4 w-4" />
            <span className="text-xs">Scan Time</span>
          </div>
          <div className="text-2xl font-bold text-foreground">
            {formatDuration(result.scan_time_ms)}
          </div>
        </div>

        <div className="rounded-lg bg-secondary/50 p-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-xs">Action Taken</span>
          </div>
          <div
            className={cn(
              'text-lg font-bold',
              result.blocked ? 'text-risk-critical' : 'text-risk-benign'
            )}
          >
            {result.blocked ? 'BLOCKED' : 'ALLOWED'}
          </div>
        </div>
      </div>

      {/* Details if available */}
      {result.details && Object.keys(result.details).length > 0 && (
        <div className="rounded-lg bg-secondary/30 p-4">
          <h4 className="text-sm font-semibold text-foreground mb-2">Analysis Details</h4>
          <pre className="text-xs font-mono text-muted-foreground overflow-x-auto">
            {JSON.stringify(result.details, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
