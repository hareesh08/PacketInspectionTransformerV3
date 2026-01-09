import { useState } from 'react';
import { Globe, Scan, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

interface UrlScannerProps {
  onScan: (url: string, blockOnDetection: boolean) => Promise<void>;
  isScanning: boolean;
}

export function UrlScanner({ onScan, isScanning }: UrlScannerProps) {
  const [url, setUrl] = useState('');
  const [blockOnDetection, setBlockOnDetection] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!url.trim()) {
      setError('Please enter a URL to scan');
      return;
    }

    try {
      new URL(url);
    } catch {
      setError('Please enter a valid URL (include https://)');
      return;
    }

    try {
      await onScan(url, blockOnDetection);
      setUrl('');
    } catch (err) {
      setError('Failed to scan URL. Please try again.');
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Globe className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-foreground">URL Scanner</h3>
          <p className="text-sm text-muted-foreground">
            Analyze URLs for malicious content
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="url" className="text-sm font-medium text-foreground">
            Target URL
          </Label>
          <div className="relative">
            <Globe className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="url"
              type="text"
              placeholder="https://example.com/path"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className={cn(
                'pl-10 font-mono text-sm bg-secondary border-border',
                error && 'border-risk-critical focus-visible:ring-risk-critical'
              )}
              disabled={isScanning}
            />
          </div>
          {error && (
            <div className="flex items-center gap-2 text-sm text-risk-critical">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <Checkbox
            id="block"
            checked={blockOnDetection}
            onCheckedChange={(checked) => setBlockOnDetection(checked as boolean)}
            disabled={isScanning}
          />
          <Label
            htmlFor="block"
            className="text-sm text-muted-foreground cursor-pointer"
          >
            Automatically block if threat detected
          </Label>
        </div>

        <Button
          type="submit"
          disabled={isScanning}
          className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
        >
          {isScanning ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Scanning...
            </>
          ) : (
            <>
              <Scan className="mr-2 h-4 w-4" />
              Scan URL
            </>
          )}
        </Button>
      </form>
    </div>
  );
}
