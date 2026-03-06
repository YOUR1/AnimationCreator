'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { JobStatusBadge } from './JobStatusBadge';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import api from '@/lib/api';
import type { GenerationStatus } from '@/types';

interface GenerationProgressProps {
  jobId: string;
  title?: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
  className?: string;
}

export function GenerationProgress({
  jobId,
  title = 'Generation',
  onComplete,
  onError,
  className,
}: GenerationProgressProps) {
  const [status, setStatus] = useState<GenerationStatus>('pending');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let pollInterval: NodeJS.Timeout | null = null;

    const handleProgress = (data: { generation: { status: GenerationStatus; progress: number; error?: string } }) => {
      setStatus(data.generation.status);
      setProgress(data.generation.progress);

      if (data.generation.status === 'completed') {
        onComplete?.();
      } else if (data.generation.status === 'failed') {
        const errorMsg = data.generation.error || 'Generation failed';
        setError(errorMsg);
        onError?.(errorMsg);
      }
    };

    const startSSE = () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3131';
        eventSource = new EventSource(`${apiUrl}/api/generate/${jobId}/stream`);

        eventSource.onopen = () => {
          setIsConnected(true);
        };

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            handleProgress(data);
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        };

        eventSource.onerror = () => {
          setIsConnected(false);
          eventSource?.close();
          // Fall back to polling if SSE fails
          startPolling();
        };
      } catch {
        // Fall back to polling if SSE is not supported
        startPolling();
      }
    };

    const startPolling = () => {
      if (pollInterval) return;

      pollInterval = setInterval(async () => {
        try {
          const response = await api.getGenerationStatus(jobId);
          handleProgress({ generation: response.generation });

          if (response.generation.status === 'completed' || response.generation.status === 'failed') {
            if (pollInterval) {
              clearInterval(pollInterval);
              pollInterval = null;
            }
          }
        } catch (e) {
          console.error('Polling error:', e);
        }
      }, 2000);
    };

    // Try SSE first, fall back to polling
    startSSE();

    return () => {
      eventSource?.close();
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [jobId, onComplete, onError]);

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-destructive" />;
      default:
        return <Loader2 className="h-5 w-5 text-primary animate-spin" />;
    }
  };

  const getStatusMessage = () => {
    switch (status) {
      case 'pending':
        return 'Waiting to start...';
      case 'processing':
        return `Processing... ${progress}%`;
      case 'completed':
        return 'Completed!';
      case 'failed':
        return error || 'Generation failed';
      default:
        return 'Unknown status';
    }
  };

  return (
    <Card className={cn('', className)}>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            {getStatusIcon()}
            <div>
              <p className="font-medium">{title}</p>
              <p className="text-sm text-muted-foreground">{getStatusMessage()}</p>
            </div>
          </div>
          <JobStatusBadge status={status} />
        </div>

        <Progress
          value={status === 'completed' ? 100 : progress}
          className={cn(
            'h-2',
            status === 'failed' && 'bg-destructive/20'
          )}
        />

        {!isConnected && status !== 'completed' && status !== 'failed' && (
          <p className="text-xs text-muted-foreground mt-2">
            Using polling for status updates...
          </p>
        )}
      </CardContent>
    </Card>
  );
}
