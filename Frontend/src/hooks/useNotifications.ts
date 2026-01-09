import { useEffect, useState, useCallback } from 'react';
import { Notification, NotificationEvent } from '@/types';
import { api } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';

interface UseNotificationsOptions {
  enabled?: boolean;
  onThreatDetected?: (notification: Notification) => void;
  onScanCompleted?: (notification: Notification) => void;
  onSystemAlert?: (notification: Notification) => void;
}

export function useNotifications({
  enabled = true,
  onThreatDetected,
  onScanCompleted,
  onSystemAlert,
}: UseNotificationsOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastNotification, setLastNotification] = useState<Notification | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const { toast } = useToast();

  const handleMessage = useCallback((notification: Notification) => {
    setLastNotification(notification);
    setNotifications((prev) => [notification, ...prev].slice(0, 50));

    // Show toast notification
    const eventType = notification.event as NotificationEvent;
    
    switch (eventType) {
      case 'threat_detected':
        toast({
          title: '🚨 Threat Detected!',
          description: `Source: ${notification.data.source || 'Unknown'} | Risk: ${notification.data.risk_level || 'Unknown'}`,
          variant: 'destructive',
          duration: 10000,
        });
        onThreatDetected?.(notification);
        break;
      
      case 'scan_completed':
        toast({
          title: '✅ Scan Completed',
          description: notification.data.message || 'Scan finished successfully',
          variant: 'default',
          duration: 5000,
        });
        onScanCompleted?.(notification);
        break;
      
      case 'system_alert':
        toast({
          title: '⚠️ System Alert',
          description: notification.data.message || 'System notification received',
          variant: 'warning',
          duration: 8000,
        });
        onSystemAlert?.(notification);
        break;
      
      case 'test':
        toast({
          title: '🔔 Test Notification',
          description: 'This is a test notification from the server',
          variant: 'default',
          duration: 3000,
        });
        break;
      
      case 'heartbeat':
        // Heartbeat - no need to show toast
        break;
    }
  }, [toast, onThreatDetected, onScanCompleted, onSystemAlert]);

  const handleError = useCallback((error: Event) => {
    console.error('Notification stream error:', error);
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (!enabled) return;

    const eventSource = api.connectNotifications(handleMessage, handleError);
    setIsConnected(true);

    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, [enabled, handleMessage, handleError]);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const sendTestNotification = useCallback(async () => {
    try {
      await api.sendTestNotification();
      return true;
    } catch (error) {
      console.error('Failed to send test notification:', error);
      return false;
    }
  }, []);

  return {
    isConnected,
    lastNotification,
    notifications,
    clearNotifications,
    sendTestNotification,
    notificationCount: notifications.length,
  };
}