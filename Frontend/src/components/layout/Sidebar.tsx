import { Link, useLocation } from 'react-router-dom';
import { Shield, LayoutDashboard, Scan, AlertTriangle, Settings, Activity, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Scanner', href: '/scanner', icon: Scan },
  { name: 'Threats', href: '/threats', icon: AlertTriangle },
  { name: 'Settings', href: '/settings', icon: Settings },
  { name: 'About', href: '/about', icon: Info },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 bg-sidebar border-r border-sidebar-border">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 px-6 border-b border-sidebar-border">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Shield className="h-6 w-6" />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-bold text-foreground">MalwareGuard</span>
          <span className="text-xs text-muted-foreground">Detection Gateway</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 p-4">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
              )}
            >
              <Icon className={cn('h-5 w-5', isActive && 'text-primary')} />
              {item.name}
              {isActive && (
                <div className="ml-auto h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Status indicator */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-sidebar-border">
        <div className="flex items-center gap-3 rounded-lg bg-sidebar-accent px-3 py-2.5">
          <div className="relative">
            <Activity className="h-4 w-4 text-risk-benign" />
            <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-risk-benign animate-pulse" />
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-medium text-foreground">System Online</span>
            <span className="text-xs text-muted-foreground">All services operational</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
