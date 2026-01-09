import { useState, useEffect, useCallback } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { ThresholdSlider } from '@/components/settings/ThresholdSlider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Settings as SettingsIcon, Save, Shield, Bell, Database, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { SettingsStatus } from '@/types';
import { toast } from 'sonner';

export default function Settings() {
  const [settings, setSettings] = useState<SettingsStatus | null>(null);
  const [threshold, setThreshold] = useState(0.7);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  const [notifications, setNotifications] = useState({
    criticalAlerts: true,
    highAlerts: true,
    mediumAlerts: false,
    dailyReport: true,
  });
  
  const [config, setConfig] = useState({
    chunkSize: 4096,
    windowSize: 512,
    autoBlock: true,
    logRetention: 30,
  });

  const fetchSettings = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const settingsData = await api.getSettings();
      setSettings(settingsData);
      setThreshold(settingsData.confidence_threshold);
      setConfig({
        chunkSize: settingsData.chunk_size,
        windowSize: settingsData.window_size,
        autoBlock: true,
        logRetention: 30,
      });
      setIsConnected(true);
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError('Failed to fetch settings');
      console.error('Settings fetch error:', apiError);
      setError(apiError.message);
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleSave = async () => {
    setIsSaving(true);

    try {
      // Update threshold via API
      const response = await api.updateThreshold(threshold);
      
      toast.success('Settings saved successfully', {
        description: `Detection threshold updated from ${response.old_threshold} to ${response.new_threshold}`,
        action: {
          label: 'Undo',
          onClick: () => handleUndoThreshold(response.old_threshold),
        },
      });
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError('Failed to save settings');
      console.error('Settings save error:', apiError);
      toast.error('Failed to save settings', {
        description: apiError.message,
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleUndoThreshold = async (oldThreshold: number) => {
    try {
      await api.updateThreshold(oldThreshold);
      setThreshold(oldThreshold);
      toast.success('Threshold restored', {
        description: `Detection threshold reverted to ${oldThreshold}`,
      });
    } catch (err) {
      toast.error('Failed to restore threshold');
    }
  };

  // Show loading state
  if (isLoading) {
    return (
      <MainLayout
        title="Settings"
        subtitle="Configure detection parameters and preferences"
      >
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">Loading settings...</span>
        </div>
      </MainLayout>
    );
  }

  // Show error state if not connected
  if (error) {
    return (
      <MainLayout
        title="Settings"
        subtitle="Configure detection parameters and preferences"
      >
        <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive mb-6">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            <p className="font-medium">Failed to connect to backend</p>
          </div>
          <p className="text-sm mt-1">{error}</p>
          <p className="text-sm mt-2">Make sure the backend is running at http://localhost:8000</p>
        </div>
      </MainLayout>
    );
  }

  // Format risk thresholds as percentages
  const riskThresholds = settings ? {
    BENIGN: `<${(settings.risk_levels.BENIGN[1] * 100).toFixed(0)}%`,
    LOW: `<${(settings.risk_levels.LOW[1] * 100).toFixed(0)}%`,
    MEDIUM: `<${(settings.risk_levels.MEDIUM[1] * 100).toFixed(0)}%`,
    HIGH: `<${(settings.risk_levels.HIGH[1] * 100).toFixed(0)}%`,
    CRITICAL: `>${(settings.risk_levels.CRITICAL[0] * 100).toFixed(0)}%`,
  } : {};

  return (
    <MainLayout
      title="Settings"
      subtitle="Configure detection parameters and preferences"
    >
      {/* Connection status indicator */}
      <div className="mb-6 flex items-center gap-2">
        <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
        <span className="text-sm text-muted-foreground">
          {isConnected ? 'Connected to backend' : 'Not connected'}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Detection Threshold */}
        <Card className="bg-card border-border">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Shield className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-foreground">Detection Threshold</CardTitle>
                <CardDescription>
                  Adjust sensitivity of the malware detection engine
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ThresholdSlider
              value={threshold}
              onChange={setThreshold}
              disabled={isSaving}
            />
            <div className="mt-4 p-3 rounded-lg bg-muted/50 text-sm">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span className="font-medium">Current: {settings?.confidence_threshold}</span>
              </div>
              <p className="text-muted-foreground text-xs">
                Higher values mean fewer false positives but more false negatives.
                Lower values are more sensitive but may have more false alarms.
              </p>
            </div>
            {/* Risk level thresholds */}
            <div className="mt-4 space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Risk Level Thresholds:</p>
              <div className="grid grid-cols-5 gap-1 text-xs">
                <div className="text-center p-1 rounded bg-green-100 text-green-800">
                  BENIGN<br/><span dangerouslySetInnerHTML={{ __html: riskThresholds.BENIGN }} />
                </div>
                <div className="text-center p-1 rounded bg-blue-100 text-blue-800">
                  LOW<br/><span dangerouslySetInnerHTML={{ __html: riskThresholds.LOW }} />
                </div>
                <div className="text-center p-1 rounded bg-yellow-100 text-yellow-800">
                  MEDIUM<br/><span dangerouslySetInnerHTML={{ __html: riskThresholds.MEDIUM }} />
                </div>
                <div className="text-center p-1 rounded bg-orange-100 text-orange-800">
                  HIGH<br/><span dangerouslySetInnerHTML={{ __html: riskThresholds.HIGH }} />
                </div>
                <div className="text-center p-1 rounded bg-red-100 text-red-800">
                  CRITICAL<br/><span dangerouslySetInnerHTML={{ __html: riskThresholds.CRITICAL }} />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card className="bg-card border-border">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Bell className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-foreground">Notifications</CardTitle>
                <CardDescription>
                  Configure alert preferences
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Critical Alerts</Label>
                <p className="text-xs text-muted-foreground">
                  Immediate notification for critical threats
                </p>
              </div>
              <Switch
                checked={notifications.criticalAlerts}
                onCheckedChange={(checked) =>
                  setNotifications((prev) => ({ ...prev, criticalAlerts: checked }))
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">High Risk Alerts</Label>
                <p className="text-xs text-muted-foreground">
                  Notify when high-risk threats are detected
                </p>
              </div>
              <Switch
                checked={notifications.highAlerts}
                onCheckedChange={(checked) =>
                  setNotifications((prev) => ({ ...prev, highAlerts: checked }))
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Medium Risk Alerts</Label>
                <p className="text-xs text-muted-foreground">
                  Notify for medium-risk threats
                </p>
              </div>
              <Switch
                checked={notifications.mediumAlerts}
                onCheckedChange={(checked) =>
                  setNotifications((prev) => ({ ...prev, mediumAlerts: checked }))
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Daily Report</Label>
                <p className="text-xs text-muted-foreground">
                  Receive daily threat summary via email
                </p>
              </div>
              <Switch
                checked={notifications.dailyReport}
                onCheckedChange={(checked) =>
                  setNotifications((prev) => ({ ...prev, dailyReport: checked }))
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* System Configuration */}
        <Card className="bg-card border-border">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <SettingsIcon className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-foreground">System Configuration</CardTitle>
                <CardDescription>
                  Advanced engine parameters
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="chunkSize" className="text-foreground">Chunk Size</Label>
                <Input
                  id="chunkSize"
                  type="number"
                  value={settings?.chunk_size || config.chunkSize}
                  readOnly
                  className="bg-muted/50 border-border cursor-not-allowed"
                  title="This value is set in the backend configuration"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="windowSize" className="text-foreground">Window Size</Label>
                <Input
                  id="windowSize"
                  type="number"
                  value={settings?.window_size || config.windowSize}
                  readOnly
                  className="bg-muted/50 border-border cursor-not-allowed"
                  title="This value is set in the backend configuration"
                />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground">Auto-Block Threats</Label>
                <p className="text-xs text-muted-foreground">
                  Automatically block high-risk content
                </p>
              </div>
              <Switch
                checked={config.autoBlock}
                onCheckedChange={(checked) =>
                  setConfig((prev) => ({ ...prev, autoBlock: checked }))
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* Data Management */}
        <Card className="bg-card border-border">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Database className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-foreground">Data Management</CardTitle>
                <CardDescription>
                  Configure data retention and storage
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="retention" className="text-foreground">Log Retention (days)</Label>
              <Input
                id="retention"
                type="number"
                value={config.logRetention}
                onChange={(e) =>
                  setConfig((prev) => ({ ...prev, logRetention: parseInt(e.target.value) }))
                }
                className="bg-secondary border-border"
              />
              <p className="text-xs text-muted-foreground">
                Threat logs older than this will be automatically archived
              </p>
            </div>
            <div className="rounded-lg bg-secondary/50 p-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Temperature</span>
                <span className="font-mono text-foreground">{settings?.temperature}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Save button */}
      <div className="mt-6 flex justify-end">
        <Button
          onClick={handleSave}
          disabled={isSaving}
          className="bg-primary text-primary-foreground hover:bg-primary/90"
        >
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Save Changes
            </>
          )}
        </Button>
      </div>
    </MainLayout>
  );
}
