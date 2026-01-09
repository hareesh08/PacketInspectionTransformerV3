import { useState, useEffect, useCallback } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { ThreatTable } from '@/components/threats/ThreatTable';
import { ThreatFilters } from '@/components/threats/ThreatFilters';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { AlertTriangle, Shield, ShieldAlert, ShieldCheck, RefreshCw, Loader2 } from 'lucide-react';
import { ThreatLog, RiskLevel, ThreatStats } from '@/types';
import { api, ApiError } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

export default function Threats() {
  const [filters, setFilters] = useState({
    risk_level: undefined as string | undefined,
    source_type: undefined as string | undefined,
    limit: 10,
    offset: 0,
  });

  const [threats, setThreats] = useState<ThreatLog[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<ThreatStats | null>(null);

  const fetchThreats = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch threats from API
      const threatsResponse = await api.getThreats({
        limit: filters.limit,
        offset: filters.offset,
        risk_level: filters.risk_level,
        source_type: filters.source_type,
      });

      setThreats(threatsResponse.threats);
      setTotal(threatsResponse.total);

      // Fetch stats
      const statsResponse = await api.getThreatStats();
      setStats(statsResponse);
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError('Failed to fetch threats');
      console.error('Threats fetch error:', apiError);
      setError(apiError.message);

      toast.error('Failed to load threats', {
        description: 'Make sure the backend is running at http://localhost:8000',
      });
    } finally {
      setIsLoading(false);
    }
  }, [filters.limit, filters.offset, filters.risk_level, filters.source_type]);

  useEffect(() => {
    fetchThreats();
  }, [fetchThreats]);

  const handleFilterChange = (newFilters: Partial<typeof filters>) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
      offset: newFilters.limit !== undefined || newFilters.risk_level !== undefined || newFilters.source_type !== undefined ? 0 : prev.offset,
    }));
  };

  const handlePageChange = (offset: number) => {
    setFilters((prev) => ({ ...prev, offset }));
  };

  const handleRefresh = () => {
    fetchThreats();
    toast.info('Refreshing threat data...');
  };

  const blockedCount = threats.filter((t) => t.blocked).length;

  return (
    <MainLayout
      title="Threat Logs"
      subtitle="View and analyze detected threats"
    >
      {/* Error banner */}
      {error && (
        <div className="mb-6 p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive">
          <p className="font-medium">Failed to connect to backend</p>
          <p className="text-sm mt-1">{error}</p>
          <p className="text-sm mt-2">Make sure the backend is running at http://localhost:8000</p>
        </div>
      )}

      {/* Refresh button */}
      <div className="flex justify-end mb-6">
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isLoading}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Loading state */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">Loading threats...</span>
        </div>
      ) : (
        <>
          {/* Quick stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <StatsCard
              title="Total Threats"
              value={stats?.total || total}
              icon={AlertTriangle}
            />
            <StatsCard
              title="Critical"
              value={stats?.critical || 0}
              icon={ShieldAlert}
              variant="danger"
            />
            <StatsCard
              title="High Risk"
              value={stats?.high || 0}
              icon={Shield}
              variant="warning"
            />
            <StatsCard
              title="Blocked"
              value={blockedCount}
              subtitle={`${((blockedCount / (stats?.total || 1)) * 100).toFixed(1)}% of threats`}
              icon={ShieldCheck}
              variant="success"
            />
          </div>

          {/* Filters */}
          <ThreatFilters filters={filters} onFilterChange={handleFilterChange} />

          {/* Table */}
          <ThreatTable
            threats={threats}
            total={total}
            limit={filters.limit}
            offset={filters.offset}
            onPageChange={handlePageChange}
          />

          {/* Data source indicator */}
          <div className="mt-4 text-xs text-muted-foreground text-center">
            Displaying {threats.length} of {total} threats from backend
          </div>
        </>
      )}
    </MainLayout>
  );
}
