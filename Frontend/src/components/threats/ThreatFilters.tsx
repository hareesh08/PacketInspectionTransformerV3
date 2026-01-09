import { Filter, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { RiskLevel, SourceType } from '@/types';

interface ThreatFiltersProps {
  filters: {
    risk_level?: string;
    source_type?: string;
    limit: number;
  };
  onFilterChange: (filters: Partial<{ risk_level?: string; source_type?: string; limit: number }>) => void;
}

export function ThreatFilters({ filters, onFilterChange }: ThreatFiltersProps) {
  const hasActiveFilters = filters.risk_level || filters.source_type;

  const clearFilters = () => {
    onFilterChange({ risk_level: undefined, source_type: undefined });
  };

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg bg-card border border-border p-4 mb-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Filter className="h-4 w-4" />
        <span>Filters:</span>
      </div>

      {/* Risk Level Filter */}
      <Select
        value={filters.risk_level || 'all'}
        onValueChange={(value) =>
          onFilterChange({ risk_level: value === 'all' ? undefined : value })
        }
      >
        <SelectTrigger className="w-[140px] bg-secondary border-border">
          <SelectValue placeholder="Risk Level" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Levels</SelectItem>
          {Object.values(RiskLevel).map((level) => (
            <SelectItem key={level} value={level}>
              {level}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Source Type Filter */}
      <Select
        value={filters.source_type || 'all'}
        onValueChange={(value) =>
          onFilterChange({ source_type: value === 'all' ? undefined : value })
        }
      >
        <SelectTrigger className="w-[120px] bg-secondary border-border">
          <SelectValue placeholder="Source" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Types</SelectItem>
          {Object.values(SourceType).map((type) => (
            <SelectItem key={type} value={type}>
              {type}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Page Size */}
      <Select
        value={filters.limit.toString()}
        onValueChange={(value) => onFilterChange({ limit: parseInt(value) })}
      >
        <SelectTrigger className="w-[100px] bg-secondary border-border">
          <SelectValue placeholder="Per page" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="10">10</SelectItem>
          <SelectItem value="25">25</SelectItem>
          <SelectItem value="50">50</SelectItem>
          <SelectItem value="100">100</SelectItem>
        </SelectContent>
      </Select>

      {/* Clear Filters */}
      {hasActiveFilters && (
        <Button
          variant="ghost"
          size="sm"
          onClick={clearFilters}
          className="text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4 mr-1" />
          Clear
        </Button>
      )}
    </div>
  );
}
