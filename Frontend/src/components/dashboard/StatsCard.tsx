import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  variant?: 'default' | 'danger' | 'warning' | 'success';
}

export function StatsCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  variant = 'default',
}: StatsCardProps) {
  const variants = {
    default: {
      iconBg: 'bg-primary/10',
      iconColor: 'text-primary',
      glow: 'hover:shadow-[0_0_30px_-5px_hsl(var(--primary)/0.3)]',
    },
    danger: {
      iconBg: 'bg-risk-critical/10',
      iconColor: 'text-risk-critical',
      glow: 'hover:shadow-[0_0_30px_-5px_hsl(var(--risk-critical)/0.3)]',
    },
    warning: {
      iconBg: 'bg-risk-high/10',
      iconColor: 'text-risk-high',
      glow: 'hover:shadow-[0_0_30px_-5px_hsl(var(--risk-high)/0.3)]',
    },
    success: {
      iconBg: 'bg-risk-benign/10',
      iconColor: 'text-risk-benign',
      glow: 'hover:shadow-[0_0_30px_-5px_hsl(var(--risk-benign)/0.3)]',
    },
  };

  const style = variants[variant];

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl border border-border bg-card p-5 transition-all duration-300',
        'hover:-translate-y-0.5',
        style.glow
      )}
    >
      {/* Top accent line */}
      <div
        className={cn(
          'absolute left-0 right-0 top-0 h-[2px]',
          variant === 'default' && 'bg-gradient-to-r from-transparent via-primary/50 to-transparent',
          variant === 'danger' && 'bg-gradient-to-r from-transparent via-risk-critical/50 to-transparent',
          variant === 'warning' && 'bg-gradient-to-r from-transparent via-risk-high/50 to-transparent',
          variant === 'success' && 'bg-gradient-to-r from-transparent via-risk-benign/50 to-transparent'
        )}
      />

      <div className="flex items-start justify-between">
        <div className="flex flex-col">
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
          <span className="mt-1 text-3xl font-bold text-foreground">{value}</span>
          {subtitle && (
            <span className="mt-1 text-xs text-muted-foreground">{subtitle}</span>
          )}
          {trend && (
            <div className="mt-2 flex items-center gap-1">
              <span
                className={cn(
                  'text-xs font-medium',
                  trend.isPositive ? 'text-risk-benign' : 'text-risk-critical'
                )}
              >
                {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}%
              </span>
              <span className="text-xs text-muted-foreground">vs last hour</span>
            </div>
          )}
        </div>

        <div className={cn('flex h-12 w-12 items-center justify-center rounded-lg', style.iconBg)}>
          <Icon className={cn('h-6 w-6', style.iconColor)} />
        </div>
      </div>
    </div>
  );
}
