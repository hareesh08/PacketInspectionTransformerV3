import { useState } from 'react';
import { Bell, Search, Terminal, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { LogViewer } from '@/components/logs/LogViewer.tsx';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { useNotifications } from '@/hooks/useNotifications';
import { Notification } from '@/types';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const [isLogViewerOpen, setIsLogViewerOpen] = useState(false);
  const { notifications, clearNotifications, notificationCount } = useNotifications();

  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return '';
    }
  };

  const getNotificationIcon = (event: string) => {
    switch (event) {
      case 'threat_detected': return '🚨';
      case 'scan_completed': return '✅';
      case 'system_alert': return '⚠️';
      case 'test': return '🔔';
      default: return '📢';
    }
  };

  return (
    <>
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/80 backdrop-blur-sm px-6">
        <div>
          <h1 className="text-xl font-bold text-foreground">{title}</h1>
          {subtitle && (
            <p className="text-sm text-muted-foreground">{subtitle}</p>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="relative hidden md:block">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search threats..."
              className="w-64 pl-9 bg-secondary border-border"
            />
          </div>

          {/* Console button */}
          <Button
            variant="outline"
            size="icon"
            className="border-border"
            onClick={() => setIsLogViewerOpen(true)}
            title="Open Live Logs"
          >
            <Terminal className="h-4 w-4" />
          </Button>

          {/* Notifications */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon" className="relative border-border">
                <Bell className="h-4 w-4" />
                {notificationCount > 0 && (
                  <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-risk-critical text-[10px] font-bold text-foreground">
                    {notificationCount > 9 ? '9+' : notificationCount}
                  </span>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <div className="flex items-center justify-between px-2 py-1.5">
                <DropdownMenuLabel>Notifications</DropdownMenuLabel>
                {notifications.length > 0 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={clearNotifications}
                    title="Clear all"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                )}
              </div>
              <DropdownMenuSeparator />
              {notifications.length === 0 ? (
                <div className="py-4 text-center text-sm text-muted-foreground">
                  No notifications yet
                </div>
              ) : (
                <div className="max-h-80 overflow-y-auto">
                  {notifications.map((notification: Notification, index: number) => (
                    <DropdownMenuItem key={`${notification.id}-${index}`} className="flex flex-col items-start gap-1 py-2 px-2">
                      <div className="flex items-center gap-2 w-full">
                        <span>{getNotificationIcon(notification.event)}</span>
                        <span className="font-medium">{notification.title || notification.event.replace('_', ' ')}</span>
                        <span className="text-xs text-muted-foreground ml-auto">
                          {formatTime(notification.timestamp)}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground ml-6">
                        {notification.message || notification.data?.message || 'No message'}
                      </p>
                    </DropdownMenuItem>
                  ))}
                </div>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* Log Viewer Modal */}
      <LogViewer
        isOpen={isLogViewerOpen}
        onClose={() => setIsLogViewerOpen(false)}
      />
    </>
  );
}
