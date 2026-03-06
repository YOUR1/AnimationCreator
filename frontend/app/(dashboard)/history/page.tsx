'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Users, Film, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import type { Generation } from '@/types';

export default function HistoryPage() {
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'character' | 'animation'>('all');

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const history = await api.getGenerationHistory();
        setGenerations(history.generations);
      } catch (error) {
        console.error('Failed to fetch history:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchHistory();
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'processing':
      case 'pending':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default">Completed</Badge>;
      case 'processing':
        return <Badge variant="secondary">Processing</Badge>;
      case 'pending':
        return <Badge variant="outline">Pending</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const filteredGenerations = generations.filter((g) => {
    if (filter === 'all') return true;
    return g.type === filter;
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Generation History</h1>
        <p className="text-muted-foreground">Track your generation requests</p>
      </div>

      <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="character">
            <Users className="h-4 w-4 mr-1" />
            Characters
          </TabsTrigger>
          <TabsTrigger value="animation">
            <Film className="h-4 w-4 mr-1" />
            Animations
          </TabsTrigger>
        </TabsList>

        <TabsContent value={filter} className="mt-6">
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-20" />
              ))}
            </div>
          ) : filteredGenerations.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-16">
                <Clock className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No generation history</h3>
                <p className="text-muted-foreground text-center mb-4">
                  Start creating characters and animations to see your history
                </p>
                <div className="flex gap-2">
                  <Link href="/characters/new">
                    <Button variant="outline">
                      <Users className="h-4 w-4 mr-2" />
                      Create Character
                    </Button>
                  </Link>
                  <Link href="/animations/new">
                    <Button variant="outline">
                      <Film className="h-4 w-4 mr-2" />
                      Create Animation
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {filteredGenerations.map((generation) => (
                <Card key={generation.id}>
                  <CardContent className="flex items-center gap-4 py-4">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full bg-muted">
                      {generation.type === 'character' ? (
                        <Users className="h-5 w-5 text-muted-foreground" />
                      ) : (
                        <Film className="h-5 w-5 text-muted-foreground" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(generation.status)}
                        <span className="font-medium capitalize">
                          {generation.type} Generation
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {new Date(generation.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      {generation.status === 'processing' && (
                        <div className="text-sm text-muted-foreground">
                          {generation.progress}%
                        </div>
                      )}
                      {getStatusBadge(generation.status)}
                      {generation.result_id && generation.status === 'completed' && (
                        <Link
                          href={`/${generation.type === 'character' ? 'characters' : 'animations'}/${generation.result_id}`}
                        >
                          <Button variant="ghost" size="sm">
                            View
                          </Button>
                        </Link>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
