import { useState } from 'react';
import { Globe, FileText, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react';
import { ThreatLog, RiskLevel, SourceType } from '@/types';
import { formatDate, formatBytes, getRiskColorClass } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface ThreatTableProps {
  threats: ThreatLog[];
  total: number;
  limit: number;
  offset: number;
  onPageChange: (offset: number) => void;
  isLoading?: boolean;
}

export function ThreatTable({
  threats,
  total,
  limit,
  offset,
  onPageChange,
  isLoading,
}: ThreatTableProps) {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  const handlePrevious = () => {
    if (offset >= limit) {
      onPageChange(offset - limit);
    }
  };

  const handleNext = () => {
    if (offset + limit < total) {
      onPageChange(offset + limit);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="text-muted-foreground">Source</TableHead>
              <TableHead className="text-muted-foreground">Type</TableHead>
              <TableHead className="text-muted-foreground">Risk Level</TableHead>
              <TableHead className="text-muted-foreground">Confidence</TableHead>
              <TableHead className="text-muted-foreground">Size</TableHead>
              <TableHead className="text-muted-foreground">Status</TableHead>
              <TableHead className="text-muted-foreground">Timestamp</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              // Loading skeleton
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i} className="border-border">
                  {Array.from({ length: 7 }).map((_, j) => (
                    <TableCell key={j}>
                      <div className="h-4 w-full animate-pulse rounded bg-secondary" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : threats.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center">
                  <div className="flex flex-col items-center justify-center text-muted-foreground">
                    <Globe className="h-8 w-8 mb-2 opacity-50" />
                    <p>No threats found</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              threats.map((threat) => (
                <TableRow
                  key={threat.id}
                  className={cn(
                    'border-border transition-colors hover:bg-secondary/50',
                    (threat.risk_level === RiskLevel.CRITICAL ||
                      threat.risk_level === RiskLevel.HIGH) &&
                      'bg-risk-critical/5'
                  )}
                >
                  <TableCell className="max-w-[200px]">
                    <div className="flex items-center gap-2">
                      {threat.source_type === SourceType.URL ? (
                        <Globe className="h-4 w-4 shrink-0 text-muted-foreground" />
                      ) : (
                        <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                      )}
                      <span className="truncate font-mono text-sm">{threat.source}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground">{threat.source_type}</span>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={cn('border', getRiskColorClass(threat.risk_level))}
                    >
                      {threat.risk_level}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-sm">
                      {(threat.probability * 100).toFixed(1)}%
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground">
                      {formatBytes(threat.bytes_scanned)}
                    </span>
                  </TableCell>
                  <TableCell>
                    {threat.blocked ? (
                      <span className="text-xs font-semibold text-risk-critical">BLOCKED</span>
                    ) : (
                      <span className="text-xs font-semibold text-risk-benign">ALLOWED</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground">
                      {formatDate(threat.timestamp)}
                    </span>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between border-t border-border px-4 py-3">
        <div className="text-sm text-muted-foreground">
          Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} results
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrevious}
            disabled={offset === 0 || isLoading}
            className="border-border"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <span className="text-sm text-muted-foreground px-2">
            Page {currentPage} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={handleNext}
            disabled={offset + limit >= total || isLoading}
            className="border-border"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
