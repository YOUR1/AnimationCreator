'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { streamJobProgress, pollJobProgress, getJobStatus, type JobProgressData } from '@/lib/generation';
import type { GenerationStatus } from '@/types';

interface UseJobProgressOptions {
  onProgress?: (data: JobProgressData) => void;
  onComplete?: (data: JobProgressData) => void;
  onError?: (error: Error) => void;
  pollInterval?: number;
  usePolling?: boolean;
}

interface UseJobProgressReturn {
  status: GenerationStatus | null;
  progress: number;
  data: JobProgressData | null;
  error: string | null;
  isComplete: boolean;
  isFailed: boolean;
  startTracking: (jobId: string) => void;
  stopTracking: () => void;
  reset: () => void;
  refetch: () => Promise<void>;
}

export function useJobProgress(options: UseJobProgressOptions = {}): UseJobProgressReturn {
  const {
    onProgress,
    onComplete,
    onError,
    pollInterval = 2000,
    usePolling = false,
  } = options;

  const [status, setStatus] = useState<GenerationStatus | null>(null);
  const [progress, setProgress] = useState(0);
  const [data, setData] = useState<JobProgressData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const jobIdRef = useRef<string | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  const handleProgress = useCallback((progressData: JobProgressData) => {
    setStatus(progressData.generation.status);
    setProgress(progressData.generation.progress);
    setData(progressData);
    onProgress?.(progressData);
  }, [onProgress]);

  const handleComplete = useCallback((progressData: JobProgressData) => {
    setStatus('completed');
    setProgress(100);
    setData(progressData);
    onComplete?.(progressData);
  }, [onComplete]);

  const handleError = useCallback((err: Error) => {
    setStatus('failed');
    setError(err.message);
    onError?.(err);
  }, [onError]);

  const startTracking = useCallback((jobId: string) => {
    // Cleanup any existing tracking
    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }

    jobIdRef.current = jobId;
    setStatus('pending');
    setProgress(0);
    setError(null);
    setData(null);

    const trackingFn = usePolling ? pollJobProgress : streamJobProgress;

    cleanupRef.current = trackingFn(
      jobId,
      {
        onProgress: handleProgress,
        onComplete: handleComplete,
        onError: handleError,
      },
      pollInterval
    );
  }, [handleProgress, handleComplete, handleError, usePolling, pollInterval]);

  const stopTracking = useCallback(() => {
    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }
    jobIdRef.current = null;
  }, []);

  const reset = useCallback(() => {
    stopTracking();
    setStatus(null);
    setProgress(0);
    setData(null);
    setError(null);
  }, [stopTracking]);

  const refetch = useCallback(async () => {
    if (!jobIdRef.current) return;

    try {
      const response = await getJobStatus(jobIdRef.current);
      const progressData: JobProgressData = {
        generation: response.generation,
        result: response.result,
      };
      handleProgress(progressData);

      if (response.generation.status === 'completed') {
        handleComplete(progressData);
      } else if (response.generation.status === 'failed') {
        handleError(new Error(response.generation.error || 'Generation failed'));
      }
    } catch (err) {
      handleError(err instanceof Error ? err : new Error('Failed to fetch status'));
    }
  }, [handleProgress, handleComplete, handleError]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
      }
    };
  }, []);

  const isComplete = status === 'completed';
  const isFailed = status === 'failed';

  return {
    status,
    progress,
    data,
    error,
    isComplete,
    isFailed,
    startTracking,
    stopTracking,
    reset,
    refetch,
  };
}

// Hook for tracking multiple jobs
interface UseMultiJobProgressOptions {
  onJobProgress?: (jobId: string, data: JobProgressData) => void;
  onJobComplete?: (jobId: string, data: JobProgressData) => void;
  onJobError?: (jobId: string, error: Error) => void;
  onAllComplete?: () => void;
}

interface JobState {
  status: GenerationStatus;
  progress: number;
  data: JobProgressData | null;
  error: string | null;
}

interface UseMultiJobProgressReturn {
  jobs: Map<string, JobState>;
  addJob: (jobId: string) => void;
  removeJob: (jobId: string) => void;
  isAllComplete: boolean;
  isAnyProcessing: boolean;
  totalProgress: number;
  reset: () => void;
}

export function useMultiJobProgress(options: UseMultiJobProgressOptions = {}): UseMultiJobProgressReturn {
  const { onJobProgress, onJobComplete, onJobError, onAllComplete } = options;

  const [jobs, setJobs] = useState<Map<string, JobState>>(new Map());
  const cleanupFns = useRef<Map<string, () => void>>(new Map());

  const addJob = useCallback((jobId: string) => {
    if (jobs.has(jobId)) return;

    const initialState: JobState = {
      status: 'pending',
      progress: 0,
      data: null,
      error: null,
    };

    setJobs((prev) => new Map(prev).set(jobId, initialState));

    const cleanup = streamJobProgress(jobId, {
      onProgress: (data) => {
        setJobs((prev) => {
          const newJobs = new Map(prev);
          newJobs.set(jobId, {
            status: data.generation.status,
            progress: data.generation.progress,
            data,
            error: data.generation.error || null,
          });
          return newJobs;
        });
        onJobProgress?.(jobId, data);
      },
      onComplete: (data) => {
        setJobs((prev) => {
          const newJobs = new Map(prev);
          newJobs.set(jobId, {
            status: 'completed',
            progress: 100,
            data,
            error: null,
          });
          return newJobs;
        });
        onJobComplete?.(jobId, data);
      },
      onError: (error) => {
        setJobs((prev) => {
          const newJobs = new Map(prev);
          const existing = prev.get(jobId);
          if (existing) {
            newJobs.set(jobId, {
              ...existing,
              status: 'failed',
              error: error.message,
            });
          }
          return newJobs;
        });
        onJobError?.(jobId, error);
      },
    });

    cleanupFns.current.set(jobId, cleanup);
  }, [jobs, onJobProgress, onJobComplete, onJobError]);

  const removeJob = useCallback((jobId: string) => {
    const cleanup = cleanupFns.current.get(jobId);
    if (cleanup) {
      cleanup();
      cleanupFns.current.delete(jobId);
    }
    setJobs((prev) => {
      const newJobs = new Map(prev);
      newJobs.delete(jobId);
      return newJobs;
    });
  }, []);

  const reset = useCallback(() => {
    cleanupFns.current.forEach((cleanup) => cleanup());
    cleanupFns.current.clear();
    setJobs(new Map());
  }, []);

  // Check if all jobs are complete
  useEffect(() => {
    if (jobs.size === 0) return;

    const allComplete = Array.from(jobs.values()).every(
      (job) => job.status === 'completed' || job.status === 'failed'
    );

    if (allComplete) {
      onAllComplete?.();
    }
  }, [jobs, onAllComplete]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupFns.current.forEach((cleanup) => cleanup());
      cleanupFns.current.clear();
    };
  }, []);

  const isAllComplete = jobs.size > 0 && Array.from(jobs.values()).every(
    (job) => job.status === 'completed' || job.status === 'failed'
  );

  const isAnyProcessing = Array.from(jobs.values()).some(
    (job) => job.status === 'pending' || job.status === 'processing'
  );

  const totalProgress = jobs.size > 0
    ? Math.round(
        Array.from(jobs.values()).reduce((sum, job) => sum + job.progress, 0) / jobs.size
      )
    : 0;

  return {
    jobs,
    addJob,
    removeJob,
    isAllComplete,
    isAnyProcessing,
    totalProgress,
    reset,
  };
}
