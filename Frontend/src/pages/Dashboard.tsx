import { useState, useEffect, useCallback } from 'react';
import { Scan, AlertTriangle, Shield, HardDrive, RefreshCw } from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { ThreatChart } from '@/components/dashboard/ThreatChart';
import { SystemHealth } from '@/components/dashboard/SystemHealth';
import { RecentThreats } from '@/components/dashboard/RecentThreats';
import { formatBytes } from '@/lib/formatters';
import { api, ApiError } from '@/lib/api';
import {
  ThreatStats,
  RiskDistribution,
  HealthStatus,
  ThreatLog,
  ThreatListResponse
} from '@/types';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

export default function Dashboard() {
  const [stats, setStats] = useState<ThreatStats | null>(null);
  const [distribution, setDistribution] = useState<RiskDistribution | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [recentThreats, setRecentThreats] = useState<ThreatLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch real data from API
      const [statsData, distributionData, healthData, threatsData] = await Promise.all([
        api.getThreatStats(),
        api.getThreatDistribution().catch(() => null),
        api.getHealth(),
        api.getThreats({ limit: 5, offset: 0, risk_level: 'HIGH,CRITICAL' }).catch(() => null),
      ]);

      setStats(statsData);
      setDistribution(distributionData || {
        BENIGN: statsData.benign || 0,
        LOW: statsData.low || 0,
        MEDIUM: statsData.medium || 0,
        HIGH: statsData.high || 0,
        CRITICAL: statsData.critical || 0,
      });
      setHealth(healthData);
      
      if (threatsData && threatsData.threats.length > 0) {
        setRecentThreats(threatsData.threats);
      }
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError('Failed to connect to backend');
      console.error('Dashboard fetch error:', apiError);
      setError(apiError.message);
      
      toast.error('Failed to load dashboard data', {
        description: 'Make sure the backend is running at http://localhost:8000',
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleRefresh = () => {
    fetchDashboardData();
    toast.info('Refreshing dashboard data...');
  };

  // Show loading state while data is being fetched
  if (isLoading) {
    return (
      <MainLayout
        title="Dashboard"
        subtitle="Real-time malware detection overview"
      >
        <div className="flex justify-end mb-4">
          <Button
            variant="outline"
            size="sm"
            disabled
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4 animate-spin" />
            Loading...
          </Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="rounded-xl border border-border bg-card p-5 animate-pulse">
              <div className="h-4 bg-muted rounded w-1/2 mb-4"></div>
              <div className="h-8 bg-muted rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-muted rounded w-1/3"></div>
            </div>
          ))}
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout
      title="Dashboard"
      subtitle="Real-time malware detection overview"
    >
      {/* Refresh button */}
      <div className="flex justify-end mb-4">
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          className="gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive">
          <p className="font-medium">Failed to connect to backend</p>
          <p className="text-sm mt-1">{error}</p>
          <p className="text-sm mt-2">Make sure the backend is running at http://localhost:8000</p>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatsCard
          title="Total Scans"
          value={stats?.total?.toLocaleString() || '0'}
          subtitle="All time"
          icon={Scan}
        />
        <StatsCard
          title="Critical Threats"
          value={stats?.critical || 0}
          subtitle="Immediate action required"
          icon={AlertTriangle}
          variant="danger"
        />
        <StatsCard
          title="High Threats"
          value={stats?.high || 0}
          subtitle="Blocked automatically"
          icon={Shield}
          variant="warning"
        />
        <StatsCard
          title="Data Scanned"
          value={formatBytes(stats?.total_bytes_scanned || 0)}
          subtitle="Total bytes analyzed"
          icon={HardDrive}
          variant="success"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <ThreatChart data={distribution} />
        <SystemHealth health={health} />
      </div>

      {/* Recent Threats */}
      <RecentThreats threats={recentThreats} />
    </MainLayout>
  );
}
