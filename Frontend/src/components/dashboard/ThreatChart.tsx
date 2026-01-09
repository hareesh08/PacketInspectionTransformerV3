import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { RiskDistribution } from '@/types';

interface ThreatChartProps {
  data: RiskDistribution | null;
}

const COLORS = {
  BENIGN: 'hsl(142, 71%, 45%)',
  LOW: 'hsl(82, 85%, 45%)',
  MEDIUM: 'hsl(48, 96%, 53%)',
  HIGH: 'hsl(25, 95%, 53%)',
  CRITICAL: 'hsl(0, 84%, 60%)',
};

const EMPTY_DATA: RiskDistribution = {
  BENIGN: 0,
  LOW: 0,
  MEDIUM: 0,
  HIGH: 0,
  CRITICAL: 0,
};

export function ThreatChart({ data }: ThreatChartProps) {
  const displayData = data || EMPTY_DATA;
  
  const chartData = [
    { name: 'Benign', value: displayData.BENIGN, color: COLORS.BENIGN },
    { name: 'Low', value: displayData.LOW, color: COLORS.LOW },
    { name: 'Medium', value: displayData.MEDIUM, color: COLORS.MEDIUM },
    { name: 'High', value: displayData.HIGH, color: COLORS.HIGH },
    { name: 'Critical', value: displayData.CRITICAL, color: COLORS.CRITICAL },
  ].filter(item => item.value > 0);

  const total = Object.values(displayData).reduce((acc, val) => acc + val, 0);

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-foreground">Threat Distribution</h3>
        <p className="text-sm text-muted-foreground">Risk level breakdown of all detected threats</p>
      </div>

      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={2}
              dataKey="value"
              stroke="hsl(var(--background))"
              strokeWidth={2}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
                color: 'hsl(var(--foreground))',
              }}
              formatter={(value: number) => [`${value} (${total > 0 ? ((value / total) * 100).toFixed(1) : 0}%)`, 'Count']}
            />
            <Legend
              layout="horizontal"
              verticalAlign="bottom"
              align="center"
              formatter={(value) => (
                <span style={{ color: 'hsl(var(--foreground))', fontSize: '12px' }}>{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Stats below chart */}
      <div className="mt-4 grid grid-cols-5 gap-2 border-t border-border pt-4">
        {Object.entries(COLORS).map(([level, color]) => (
          <div key={level} className="text-center">
            <div
              className="mx-auto mb-1 h-2 w-2 rounded-full"
              style={{ backgroundColor: color }}
            />
            <div className="text-xs text-muted-foreground capitalize">{level.toLowerCase()}</div>
            <div className="text-sm font-semibold text-foreground">
              {displayData[level as keyof RiskDistribution]}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
