import { Slider } from '@/components/ui/slider';
import { cn } from '@/lib/utils';

interface ThresholdSliderProps {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}

export function ThresholdSlider({ value, onChange, disabled }: ThresholdSliderProps) {
  const getThresholdColor = (val: number) => {
    if (val < 0.3) return 'text-risk-critical';
    if (val < 0.5) return 'text-risk-high';
    if (val < 0.7) return 'text-risk-medium';
    if (val < 0.9) return 'text-risk-low';
    return 'text-risk-benign';
  };

  const getThresholdDescription = (val: number) => {
    if (val < 0.3) return 'Very aggressive - High false positive rate';
    if (val < 0.5) return 'Aggressive - More false positives';
    if (val < 0.7) return 'Balanced - Recommended for most use cases';
    if (val < 0.9) return 'Conservative - More false negatives';
    return 'Very conservative - Minimal detections';
  };

  return (
    <div className="space-y-6">
      {/* Current value display */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-sm text-muted-foreground">Current Threshold</span>
          <div className={cn('text-4xl font-bold', getThresholdColor(value))}>
            {(value * 100).toFixed(0)}%
          </div>
        </div>
        <div className="text-right">
          <span className="text-xs text-muted-foreground">Sensitivity Level</span>
          <div className="text-sm text-foreground">{getThresholdDescription(value)}</div>
        </div>
      </div>

      {/* Slider */}
      <div className="pt-2">
        <Slider
          value={[value]}
          min={0}
          max={1}
          step={0.01}
          onValueChange={([val]) => onChange(val)}
          disabled={disabled}
          className="cursor-pointer"
        />

        {/* Scale labels */}
        <div className="flex justify-between mt-2 text-xs text-muted-foreground">
          <span>0% (Detect all)</span>
          <span>50%</span>
          <span>100% (High confidence only)</span>
        </div>
      </div>

      {/* Risk level indicators */}
      <div className="grid grid-cols-5 gap-1 rounded-lg overflow-hidden">
        <div className="h-2 bg-risk-critical" />
        <div className="h-2 bg-risk-high" />
        <div className="h-2 bg-risk-medium" />
        <div className="h-2 bg-risk-low" />
        <div className="h-2 bg-risk-benign" />
      </div>

      {/* Info box */}
      <div className="rounded-lg bg-secondary/50 p-4">
        <h4 className="text-sm font-semibold text-foreground mb-2">About Detection Threshold</h4>
        <p className="text-xs text-muted-foreground leading-relaxed">
          The detection threshold determines the minimum confidence score required to flag content
          as potentially malicious. A lower threshold (more aggressive) will catch more threats but
          may produce more false positives. A higher threshold (more conservative) will only flag
          high-confidence threats but may miss some attacks.
        </p>
      </div>
    </div>
  );
}
