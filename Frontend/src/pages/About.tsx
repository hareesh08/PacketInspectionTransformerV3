import { useState, useEffect } from 'react';
import { 
  Shield, 
  Server, 
  Github, 
  Mail, 
  Users, 
  Code, 
  Cpu, 
  Database, 
  Activity,
  ExternalLink
} from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api, ApiError } from '@/lib/api';
import { HealthStatus } from '@/types';

interface TeamMember {
  name: string;
  role: string;
  github: string;
  email: string;
  avatar: string;
}

const teamMembers: TeamMember[] = [
  {
    name: 'Gnana Pragadeesh K',
    role: 'Lead Developer',
    github: 'https://github.com/NexusSRC',
    email: 'gnanapragadeeshoffcl@gmail.com',
    avatar: 'GP'
  },
  {
    name: 'Hareesh D',
    role: 'Backend Engineer',
    github: 'https://github.com/hareesh08',
    email: 'hareeshworksoffcial@gmail.com',
    avatar: 'HD'
  }
];

export default function About() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const healthData = await api.getHealth();
        setHealth(healthData);
      } catch (err) {
        const apiError = err instanceof ApiError ? err : new ApiError('Failed to fetch health status');
        setError(apiError.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchHealth();
  }, []);

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  return (
    <MainLayout
      title="About"
      subtitle="Learn more about MalwareGuard and our team"
    >
      <div className="space-y-8">
        {/* Project Overview */}
        <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-background">
          <CardHeader className="text-center pb-2">
            <div className="flex justify-center mb-4">
              <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <Shield className="h-10 w-10" />
              </div>
            </div>
            <CardTitle className="text-3xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
              MalwareGuard
            </CardTitle>
            <CardDescription className="text-lg max-w-2xl mx-auto">
              Advanced Real-Time Malware Detection Gateway powered by Machine Learning
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <p className="text-muted-foreground max-w-3xl mx-auto leading-relaxed">
              MalwareGuard is a state-of-the-art threat detection system designed to protect your 
              infrastructure from malicious URLs and files. Built with cutting-edge transformer 
              technology, our system provides real-time analysis and classification with high accuracy.
              The system monitors network traffic, analyzes suspicious content, and blocks potential 
              threats before they can cause harm to your systems.
            </p>
            <div className="flex justify-center gap-3 flex-wrap">
              <Badge variant="outline" className="px-4 py-2 text-sm">
                <Code className="h-4 w-4 mr-2" />
                Transformer-based AI
              </Badge>
              <Badge variant="outline" className="px-4 py-2 text-sm">
                <Activity className="h-4 w-4 mr-2" />
                Real-time Detection
              </Badge>
              <Badge variant="outline" className="px-4 py-2 text-sm">
                <Shield className="h-4 w-4 mr-2" />
                ML-Powered Security
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* VM Server Status */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* System Health */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5 text-primary" />
                VM Server Status
              </CardTitle>
              <CardDescription>
                Real-time monitoring of the backend infrastructure
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4 animate-pulse">
                  <div className="h-6 bg-muted rounded w-1/3"></div>
                  <div className="h-4 bg-muted rounded w-2/3"></div>
                  <div className="h-4 bg-muted rounded w-1/2"></div>
                </div>
              ) : error ? (
                <div className="text-center py-8">
                  <div className="flex justify-center mb-4">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10 text-destructive">
                      <Server className="h-8 w-8" />
                    </div>
                  </div>
                  <p className="text-destructive font-medium">Unable to connect to server</p>
                  <p className="text-sm text-muted-foreground mt-1">{error}</p>
                  <Button 
                    variant="outline" 
                    className="mt-4"
                    onClick={() => window.location.reload()}
                  >
                    Retry Connection
                  </Button>
                </div>
              ) : health ? (
                <div className="space-y-6">
                  {/* Overall Status */}
                  <div className="flex items-center justify-between p-4 rounded-lg bg-background border">
                    <div className="flex items-center gap-3">
                      <div className={`h-3 w-3 rounded-full ${
                        health.status === 'healthy' 
                          ? 'bg-risk-benign animate-pulse' 
                          : health.status === 'degraded'
                          ? 'bg-risk-medium animate-pulse'
                          : 'bg-risk-critical animate-pulse'
                      }`} />
                      <span className="font-medium">System Status</span>
                    </div>
                    <Badge variant={
                      health.status === 'healthy' ? 'default' :
                      health.status === 'degraded' ? 'secondary' : 'destructive'
                    }>
                      {health.status.toUpperCase()}
                    </Badge>
                  </div>

                  {/* Uptime */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-4 rounded-lg bg-muted/50">
                      <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <Activity className="h-4 w-4" />
                        <span className="text-xs">Uptime</span>
                      </div>
                      <p className="text-2xl font-bold">{formatUptime(health.uptime_seconds)}</p>
                    </div>
                    <div className="p-4 rounded-lg bg-muted/50">
                      <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <Cpu className="h-4 w-4" />
                        <span className="text-xs">Memory</span>
                      </div>
                      <p className="text-2xl font-bold">{health.memory_usage_mb.toFixed(1)} MB</p>
                    </div>
                    <div className="p-4 rounded-lg bg-muted/50">
                      <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <Database className="h-4 w-4" />
                        <span className="text-xs">Database</span>
                      </div>
                      <p className="text-2xl font-bold">
                        {health.database.connected ? (
                          <span className="text-risk-benign">Connected</span>
                        ) : (
                          <span className="text-risk-critical">Offline</span>
                        )}
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-muted/50">
                      <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <Server className="h-4 w-4" />
                        <span className="text-xs">Threats</span>
                      </div>
                      <p className="text-2xl font-bold">{health.database.total_threats}</p>
                    </div>
                  </div>

                  {/* Model Status */}
                  <div className="p-4 rounded-lg border bg-muted/30">
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-medium flex items-center gap-2">
                        <Shield className="h-4 w-4 text-primary" />
                        AI Model Status
                      </span>
                      <Badge variant={health.model.loaded ? 'default' : 'destructive'}>
                        {health.model.loaded ? 'Loaded' : 'Not Loaded'}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Device:</span>
                        <span className="ml-2 font-medium">{health.model.device}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Parameters:</span>
                        <span className="ml-2 font-medium">{(health.model.parameters || 0).toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Vocab Size:</span>
                        <span className="ml-2 font-medium">{health.model.vocab_size}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Layers:</span>
                        <span className="ml-2 font-medium">{health.model.num_layers}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          {/* Quick Stats */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                Quick Stats
              </CardTitle>
              <CardDescription>
                System performance metrics
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <span className="text-sm text-muted-foreground">API Status</span>
                <Badge variant="outline" className="bg-risk-benign/10 text-risk-benign border-risk-benign">
                  Operational
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <span className="text-sm text-muted-foreground">Database</span>
                <Badge variant="outline" className="bg-risk-benign/10 text-risk-benign border-risk-benign">
                  Active
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <span className="text-sm text-muted-foreground">ML Model</span>
                <Badge variant="outline" className="bg-risk-benign/10 text-risk-benign border-risk-benign">
                  Ready
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <span className="text-sm text-muted-foreground">Version</span>
                <span className="text-sm font-mono">v1.0.0</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Team Section */}
        <Card>
          <CardHeader className="text-center">
            <CardTitle className="flex items-center justify-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              Meet the Team
            </CardTitle>
            <CardDescription>
              The developers behind MalwareGuard
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
              {teamMembers.map((member, index) => (
                <div 
                  key={member.name}
                  className="relative group"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-primary/5 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  <div className="relative p-6 rounded-xl border bg-card hover:shadow-lg transition-all duration-300">
                    <div className="flex items-start gap-4">
                      {/* Avatar */}
                      <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold text-xl shrink-0">
                        {member.avatar}
                      </div>
                      
                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <h3 className="font-bold text-lg truncate">{member.name}</h3>
                        <p className="text-sm text-primary font-medium mb-3">{member.role}</p>
                        
                        {/* Links */}
                        <div className="space-y-2">
                          <a 
                            href={member.github} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors"
                          >
                            <Github className="h-4 w-4" />
                            <span className="truncate">GitHub Profile</span>
                            <ExternalLink className="h-3 w-3 ml-auto shrink-0" />
                          </a>
                          <a 
                            href={`mailto:${member.email}`}
                            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors"
                          >
                            <Mail className="h-4 w-4" />
                            <span className="truncate">{member.email}</span>
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Technology Stack */}
        <Card className="bg-gradient-to-br from-muted/50 to-background">
          <CardHeader className="text-center">
            <CardTitle>Technology Stack</CardTitle>
            <CardDescription>
              Built with modern technologies for performance and reliability
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
              {[
                { name: 'Python', desc: 'Backend API', icon: '🐍' },
                { name: 'PyTorch', desc: 'ML Framework', icon: '🔥' },
                { name: 'React', desc: 'Frontend UI', icon: '⚛️' },
                { name: 'TypeScript', desc: 'Type Safety', icon: '📘' },
                { name: 'Transformer', desc: 'ML Architecture', icon: '🧠' },
                { name: 'Vite', desc: 'Build Tool', icon: '⚡' },
                { name: 'Tailwind', desc: 'Styling', icon: '🎨' },
                { name: 'SQLite', desc: 'Database', icon: '🗄️' },
              ].map((tech) => (
                <div 
                  key={tech.name}
                  className="p-4 rounded-lg border bg-background hover:shadow-md transition-shadow text-center"
                >
                  <div className="text-3xl mb-2">{tech.icon}</div>
                  <p className="font-medium text-sm">{tech.name}</p>
                  <p className="text-xs text-muted-foreground">{tech.desc}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center text-sm text-muted-foreground">
          <p>MalwareGuard v1.0.0 • Real-Time Malware Detection Gateway</p>
          <p className="mt-1">
            Built with ❤️ by{' '}
            <span className="font-medium">Gnana Pragadeesh</span> and{' '}
            <span className="font-medium">Hareesh D</span>
          </p>
        </div>
      </div>
    </MainLayout>
  );
}
