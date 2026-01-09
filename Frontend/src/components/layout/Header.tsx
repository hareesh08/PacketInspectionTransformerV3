import { Bell, Search, Terminal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  return (
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
        <Button variant="outline" size="icon" className="border-border">
          <Terminal className="h-4 w-4" />
        </Button>

        {/* Notifications */}
        <Button variant="outline" size="icon" className="relative border-border">
          <Bell className="h-4 w-4" />
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-risk-critical text-[10px] font-bold text-foreground">
            3
          </span>
        </Button>
      </div>
    </header>
  );
}
