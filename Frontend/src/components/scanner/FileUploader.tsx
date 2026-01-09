import { useState, useCallback } from 'react';
import { Upload, FileText, X, Loader2, Scan, AlertCircle, Zap, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';
import { formatBytes } from '@/lib/formatters';

interface FileUploaderProps {
  onUpload: (file: File, blockOnDetection: boolean, earlyTermination: boolean) => Promise<void>;
  isScanning: boolean;
}

export function FileUploader({ onUpload, isScanning }: FileUploaderProps) {
  const [file, setFile] = useState<File | null>(null);
  const [blockOnDetection, setBlockOnDetection] = useState(true);
  const [earlyTermination, setEarlyTermination] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    setError(null);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!file) {
      setError('Please select a file to scan');
      return;
    }

    try {
      await onUpload(file, blockOnDetection, earlyTermination);
      setFile(null);
    } catch {
      setError('Failed to scan file. Please try again.');
    }
  };

  const clearFile = () => {
    setFile(null);
    setError(null);
  };

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Upload className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-foreground">File Scanner</h3>
          <p className="text-sm text-muted-foreground">
            Upload files for malware analysis
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Drop zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            'relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-all',
            isDragOver
              ? 'border-primary bg-primary/5'
              : 'border-border bg-secondary/30 hover:border-primary/50',
            error && 'border-risk-critical',
            isScanning && 'pointer-events-none opacity-50'
          )}
        >
          {file ? (
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div className="text-left">
                <div className="font-medium text-foreground truncate max-w-[200px]">
                  {file.name}
                </div>
                <div className="text-sm text-muted-foreground">
                  {formatBytes(file.size)}
                </div>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={clearFile}
                disabled={isScanning}
                className="h-8 w-8"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <>
              <Upload className="h-10 w-10 text-muted-foreground mb-3" />
              <p className="text-sm text-foreground font-medium">
                Drop a file here or click to browse
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Supported: executables, documents, archives
              </p>
            </>
          )}
          <input
            type="file"
            className="absolute inset-0 cursor-pointer opacity-0"
            onChange={handleFileChange}
            disabled={isScanning}
          />
        </div>

        {error && (
          <div className="flex items-center gap-2 text-sm text-risk-critical">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        <div className="flex items-center justify-between rounded-lg bg-secondary/50 p-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10">
              <Shield className="h-4 w-4 text-primary" />
            </div>
            <div>
              <Label htmlFor="block-file" className="text-sm font-medium cursor-pointer">
                Auto-block threats
              </Label>
              <p className="text-xs text-muted-foreground">
                Block access when malware detected
              </p>
            </div>
          </div>
          <Checkbox
            id="block-file"
            checked={blockOnDetection}
            onCheckedChange={(checked) => setBlockOnDetection(checked as boolean)}
            disabled={isScanning}
          />
        </div>

        <div className="flex items-center justify-between rounded-lg bg-secondary/50 p-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-risk-high/10">
              <Zap className="h-4 w-4 text-risk-high" />
            </div>
            <div>
              <Label htmlFor="early-termination" className="text-sm font-medium cursor-pointer">
                Fast Block Mode
              </Label>
              <p className="text-xs text-muted-foreground">
                Stop at 1KB for high-confidence threats
              </p>
            </div>
          </div>
          <Switch
            id="early-termination"
            checked={earlyTermination}
            onCheckedChange={setEarlyTermination}
            disabled={isScanning}
          />
        </div>

        <Button
          type="submit"
          disabled={isScanning || !file}
          className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
        >
          {isScanning ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Scan className="mr-2 h-4 w-4" />
              Scan File
            </>
          )}
        </Button>
      </form>
    </div>
  );
}
