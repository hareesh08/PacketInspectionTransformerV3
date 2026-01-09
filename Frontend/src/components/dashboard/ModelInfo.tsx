import { useEffect, useState } from 'react';
import { Cpu, HardDrive, Zap, Activity, MemoryStick, Layers } from 'lucide-react';
import { cn, formatBytes, formatNumber } from '@/lib/utils';
import { ModelInfoResponse } from '@/types';
import { api } from '@/lib/api';

interface ModelInfoProps {
  initialData?: ModelInfoResponse;
  refreshInterval?: number;
}

export function ModelInfo({ initialData, refreshInterval = 10000 }: ModelInfoProps) {
  const [modelInfo, setModelInfo] = useState<ModelInfoResponse | null>(initialData || null);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchModelInfo = async () => {
      try {
        const data = await api.getModelInfo();
        setModelInfo(data);
        setError(null);
      } catch (err) {
        setError('Failed to load model info');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchModelInfo();
    const interval = setInterval(fetchModelInfo, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-foreground">Model Information</h3>
          <p className="text-sm text-muted-foreground">Loading model details...</p>
        </div>
        <div className="space-y-4">
          <div className="animate-pulse rounded-lg bg-secondary/50 h-16" />
          <div className="animate-pulse rounded-lg bg-secondary/50 h-16" />
          <div className="animate-pulse rounded-lg bg-secondary/50 h-16" />
        </div>
      </div>
    );
  }

  if (error || !modelInfo) {
    return (
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-foreground">Model Information</h3>
          <p className="text-sm text-muted-foreground">Unable to load model details</p>
        </div>
        <div className="rounded-lg bg-risk-critical/10 p-4 text-risk-critical">
          {error || 'Unknown error'}
        </div>
      </div>
    );
  }

  const { cpu, memory, gpu, model, device, device_type, uptime_seconds } = modelInfo;

  const formatUptime = (seconds: number): string => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hrs}h ${mins}m`;
  };

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Model Information</h3>
          <p className="text-sm text-muted-foreground">
            {model.loaded ? `Running on ${device_type}` : 'Model not loaded'}
          </p>
        </div>
        <div className={cn(
          'flex items-center gap-2 rounded-full px-3 py-1',
          model.loaded ? 'bg-risk-benign/10' : 'bg-risk-critical/10'
        )}>
          <Zap className={cn(
            'h-4 w-4',
            model.loaded ? 'text-risk-benign' : 'text-risk-critical'
          )} />
          <span className={cn(
            'text-sm font-medium capitalize',
            model.loaded ? 'text-risk-benign' : 'text-risk-critical'
          )}>
            {device}
          </span>
        </div>
      </div>

      <div className="space-y-4">
        {/* Model Core Info */}
        <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <Layers className="h-4 w-4 text-primary" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">Transformer Model</div>
              <div className="text-xs text-muted-foreground">
                {model.d_model}d model, {model.num_layers} layers, {model.nhead} heads
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-foreground">
              {formatNumber(model.total_parameters)} params
            </div>
            <div className="text-xs text-muted-foreground">
              Vocab: {model.vocab_size}
            </div>
          </div>
        </div>

        {/* CPU Info */}
        <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <Cpu className="h-4 w-4 text-primary" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">CPU</div>
              <div className="text-xs text-muted-foreground">
                {cpu.physical_cores} physical, {cpu.logical_cores} logical cores
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-foreground">
              {cpu.cpu_percent.toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground">
              {cpu.frequency_mhz ? `${cpu.frequency_mhz.toFixed(0)} MHz` : 'N/A'}
            </div>
          </div>
        </div>

        {/* Memory Info */}
        <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <MemoryStick className="h-4 w-4 text-primary" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">Memory</div>
              <div className="text-xs text-muted-foreground">
                {formatBytes(memory.used_gb * 1024 * 1024 * 1024)} / {formatBytes(memory.total_gb * 1024 * 1024 * 1024)}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-foreground">
              {memory.percent_used.toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground">
              {formatBytes(memory.available_gb * 1024 * 1024 * 1024)} available
            </div>
          </div>
        </div>

        {/* GPU Info (if available) */}
        {gpu.available && (
          <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-risk-high/10">
                <Activity className="h-4 w-4 text-risk-high" />
              </div>
              <div>
                <div className="text-sm font-medium text-foreground">GPU</div>
                <div className="text-xs text-muted-foreground">
                  {gpu.device_name || 'Unknown'}
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium text-foreground">
                {gpu.total_memory_gb?.toFixed(1) || 0} GB
              </div>
              <div className="text-xs text-muted-foreground">
                {gpu.allocated_memory_gb?.toFixed(2) || 0} GB allocated
              </div>
            </div>
          </div>
        )}

        {/* Uptime */}
        <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <HardDrive className="h-4 w-4 text-primary" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">System Uptime</div>
              <div className="text-xs text-muted-foreground">Server running time</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-foreground">
              {formatUptime(uptime_seconds)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}