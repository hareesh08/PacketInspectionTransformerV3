import { useState, useCallback } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { UrlScanner } from '@/components/scanner/UrlScanner';
import { FileUploader } from '@/components/scanner/FileUploader';
import { ScanResult as ScanResultComponent } from '@/components/scanner/ScanResult';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Globe, FileText, History, Trash2, Loader2 } from 'lucide-react';
import { ScanResult, RiskLevel, SourceType, ScanStatus } from '@/types';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { formatRelativeTime, getRiskColorClass } from '@/lib/formatters';
import { Badge } from '@/components/ui/badge';
import { api, ApiError } from '@/lib/api';
import { toast } from 'sonner';

export default function Scanner() {
  const [isScanning, setIsScanning] = useState(false);
  const [currentResult, setCurrentResult] = useState<ScanResult | null>(null);
  const [scanHistory, setScanHistory] = useState<ScanResult[]>([]);

  const handleUrlScan = useCallback(async (url: string, blockOnDetection: boolean, earlyTermination: boolean) => {
    setIsScanning(true);
    setCurrentResult(null);

    try {
      toast.info('Scanning URL...', {
        description: url,
      });

      const result = await api.scanUrl(url, blockOnDetection, earlyTermination);
      
      setCurrentResult(result);
      setScanHistory((prev) => [result, ...prev.slice(0, 49)]);
      
      toast.success(result.status === ScanStatus.CLEAN ? 'URL is safe' : 'Threat detected', {
        description: `Risk level: ${result.risk_level} (${(result.probability * 100).toFixed(1)}%)`,
      });
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError('URL scan failed');
      console.error('URL scan error:', apiError);
      
      toast.error('Scan failed', {
        description: apiError.message,
      });
      
      // Create an error result for display
      const errorResult: ScanResult = {
        source: url,
        source_type: SourceType.URL,
        probability: 0,
        risk_level: RiskLevel.BENIGN,
        bytes_scanned: 0,
        blocked: false,
        scan_time_ms: 0,
        status: ScanStatus.ERROR,
        details: { error: apiError.message },
        timestamp: new Date().toISOString(),
      };
      setCurrentResult(errorResult);
    } finally {
      setIsScanning(false);
    }
  }, []);

  const handleFileUpload = useCallback(async (file: File, blockOnDetection: boolean, earlyTermination: boolean) => {
    setIsScanning(true);
    setCurrentResult(null);

    try {
      toast.info('Scanning file...', {
        description: file.name,
      });

      const result = await api.scanFile(file, blockOnDetection, earlyTermination);
      
      setCurrentResult(result);
      setScanHistory((prev) => [result, ...prev.slice(0, 49)]);
      
      toast.success(result.status === ScanStatus.CLEAN ? 'File is safe' : 'Threat detected', {
        description: `Risk level: ${result.risk_level} (${(result.probability * 100).toFixed(1)}%)`,
      });
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError('File scan failed');
      console.error('File scan error:', apiError);
      
      toast.error('Scan failed', {
        description: apiError.message,
      });
      
      // Create an error result for display
      const errorResult: ScanResult = {
        source: file.name,
        source_type: SourceType.FILE,
        probability: 0,
        risk_level: RiskLevel.BENIGN,
        bytes_scanned: 0,
        blocked: false,
        scan_time_ms: 0,
        status: ScanStatus.ERROR,
        details: { error: apiError.message },
        timestamp: new Date().toISOString(),
      };
      setCurrentResult(errorResult);
    } finally {
      setIsScanning(false);
    }
  }, []);

  const clearHistory = () => {
    setScanHistory([]);
    setCurrentResult(null);
    toast.info('Scan history cleared');
  };

  return (
    <MainLayout
      title="Malware Scanner"
      subtitle="Scan URLs and files for malicious content"
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scanner tabs */}
        <div className="lg:col-span-2">
          <Tabs defaultValue="url" className="space-y-4">
            <TabsList className="grid w-full grid-cols-2 bg-secondary">
              <TabsTrigger value="url" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                <Globe className="h-4 w-4 mr-2" />
                URL Scanner
              </TabsTrigger>
              <TabsTrigger value="file" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                <FileText className="h-4 w-4 mr-2" />
                File Scanner
              </TabsTrigger>
            </TabsList>

            <TabsContent value="url">
              <UrlScanner onScan={handleUrlScan} isScanning={isScanning} />
            </TabsContent>

            <TabsContent value="file">
              <FileUploader onUpload={handleFileUpload} isScanning={isScanning} />
            </TabsContent>
          </Tabs>

          {/* Current result */}
          {currentResult && (
            <div className="mt-6">
              <ScanResultComponent result={currentResult} />
            </div>
          )}

          {/* Loading overlay */}
          {isScanning && (
            <div className="mt-6 p-4 rounded-lg border border-primary/20 bg-primary/5 flex items-center justify-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span className="text-sm text-muted-foreground">Analyzing...</span>
            </div>
          )}
        </div>

        {/* Scan history */}
        <div className="lg:col-span-1">
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <History className="h-5 w-5 text-primary" />
                <h3 className="text-lg font-semibold text-foreground">Scan History</h3>
                {scanHistory.length > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {scanHistory.length}
                  </Badge>
                )}
              </div>
              {scanHistory.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearHistory}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>

            {scanHistory.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <History className="h-8 w-8 text-muted-foreground/50 mb-2" />
                <p className="text-sm text-muted-foreground">No scans yet</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Scan a URL or file to see results here
                </p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[500px] overflow-y-auto">
                {scanHistory.map((result, index) => (
                  <div
                    key={`${result.timestamp}-${index}`}
                    className={cn(
                      'flex items-center gap-3 rounded-lg bg-secondary/50 px-3 py-2 cursor-pointer transition-colors hover:bg-secondary',
                      currentResult === result && 'ring-1 ring-primary'
                    )}
                    onClick={() => setCurrentResult(result)}
                  >
                    {result.source_type === SourceType.URL ? (
                      <Globe className="h-4 w-4 shrink-0 text-muted-foreground" />
                    ) : (
                      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="truncate text-sm font-mono">
                        {result.source.length > 30 
                          ? `${result.source.substring(0, 30)}...` 
                          : result.source}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatRelativeTime(result.timestamp)}
                        {result.status === ScanStatus.ERROR && ' • Error'}
                      </div>
                    </div>
                    <Badge
                      variant="outline"
                      className={cn('shrink-0 border text-xs', getRiskColorClass(result.risk_level))}
                    >
                      {result.risk_level}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick stats */}
          {scanHistory.length > 0 && (
            <div className="mt-4 rounded-xl border border-border bg-card p-5">
              <h4 className="text-sm font-medium text-muted-foreground mb-3">Session Stats</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-2 rounded-lg bg-secondary/50">
                  <div className="text-lg font-bold text-foreground">
                    {scanHistory.filter(r => r.status === ScanStatus.THREAT_DETECTED).length}
                  </div>
                  <div className="text-xs text-muted-foreground">Threats Detected</div>
                </div>
                <div className="text-center p-2 rounded-lg bg-secondary/50">
                  <div className="text-lg font-bold text-foreground">
                    {scanHistory.filter(r => r.status === ScanStatus.CLEAN).length}
                  </div>
                  <div className="text-xs text-muted-foreground">Clean Results</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
