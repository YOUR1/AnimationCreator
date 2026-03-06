'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import api from '@/lib/api';
import { streamJobProgress, pollJobProgress, type JobProgressData } from '@/lib/generation';
import type { Generation, Animation, GenerationStatus, AnimationType } from '@/types';

interface AnimationGenerationParams {
  characterId: string;
  type: AnimationType;
  name: string;
  prompt?: string;
  duration?: number;
  fps?: number;
  format?: 'mp4' | 'gif' | 'webm';
}

interface AnimationJobStatus {
  id: string;
  type: AnimationType;
  status: GenerationStatus;
  progress: number;
  animation?: Animation;
  error?: string;
}

interface UseAnimationGenerationReturn {
  generate: (params: AnimationGenerationParams) => Promise<string>;
  generateBatch: (params: Omit<AnimationGenerationParams, 'type' | 'name'>[], types: AnimationType[]) => Promise<string[]>;
  jobs: AnimationJobStatus[];
  isGenerating: boolean;
  completedAnimations: Animation[];
  error: string | null;
  reset: () => void;
  cancelAll: () => void;
}

export function useAnimationGeneration(): UseAnimationGenerationReturn {
  const [jobs, setJobs] = useState<AnimationJobStatus[]>([]);
  const [error, setError] = useState<string | null>(null);
  const cleanupFns = useRef<Map<string, () => void>>(new Map());

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupFns.current.forEach((cleanup) => cleanup());
      cleanupFns.current.clear();
    };
  }, []);

  const trackJob = useCallback((jobId: string, type: AnimationType) => {
    const handleProgress = (data: JobProgressData) => {
      setJobs((prev) =>
        prev.map((job) =>
          job.id === jobId
            ? {
                ...job,
                status: data.generation.status,
                progress: data.generation.progress,
                animation: data.result as Animation | undefined,
                error: data.generation.error,
              }
            : job
        )
      );
    };

    const handleComplete = (data: JobProgressData) => {
      handleProgress(data);
    };

    const handleError = (err: Error) => {
      setJobs((prev) =>
        prev.map((job) =>
          job.id === jobId
            ? { ...job, status: 'failed' as GenerationStatus, error: err.message }
            : job
        )
      );
    };

    // Try SSE first, fall back to polling
    let cleanup: () => void;
    try {
      cleanup = streamJobProgress(jobId, {
        onProgress: handleProgress,
        onComplete: handleComplete,
        onError: handleError,
      });
    } catch {
      cleanup = pollJobProgress(jobId, {
        onProgress: handleProgress,
        onComplete: handleComplete,
        onError: handleError,
      });
    }

    cleanupFns.current.set(jobId, cleanup);
  }, []);

  const generate = useCallback(async (params: AnimationGenerationParams): Promise<string> => {
    setError(null);

    try {
      const generation = await api.createAnimation({
        character_id: params.characterId,
        type: params.type,
        name: params.name,
        options: {
          duration: params.duration,
          custom_prompt: params.prompt,
        },
      });

      const newJob: AnimationJobStatus = {
        id: generation.id,
        type: params.type,
        status: 'pending',
        progress: 0,
      };

      setJobs((prev) => [...prev, newJob]);
      trackJob(generation.id, params.type);

      return generation.id;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start animation generation';
      setError(errorMessage);
      throw err;
    }
  }, [trackJob]);

  const generateBatch = useCallback(async (
    baseParams: Omit<AnimationGenerationParams, 'type' | 'name'>[],
    types: AnimationType[]
  ): Promise<string[]> => {
    setError(null);
    const jobIds: string[] = [];

    try {
      for (let i = 0; i < types.length; i++) {
        const type = types[i];
        const params = baseParams[i] || baseParams[0];

        const generation = await api.createAnimation({
          character_id: params.characterId,
          type,
          name: `${type} animation`,
          options: {
            duration: params.duration,
            custom_prompt: params.prompt,
          },
        });

        const newJob: AnimationJobStatus = {
          id: generation.id,
          type,
          status: 'pending',
          progress: 0,
        };

        setJobs((prev) => [...prev, newJob]);
        trackJob(generation.id, type);
        jobIds.push(generation.id);
      }

      return jobIds;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start animation generation';
      setError(errorMessage);
      throw err;
    }
  }, [trackJob]);

  const reset = useCallback(() => {
    cleanupFns.current.forEach((cleanup) => cleanup());
    cleanupFns.current.clear();
    setJobs([]);
    setError(null);
  }, []);

  const cancelAll = useCallback(() => {
    cleanupFns.current.forEach((cleanup) => cleanup());
    cleanupFns.current.clear();
  }, []);

  const isGenerating = jobs.some(
    (job) => job.status === 'pending' || job.status === 'processing'
  );

  const completedAnimations = jobs
    .filter((job) => job.status === 'completed' && job.animation)
    .map((job) => job.animation as Animation);

  return {
    generate,
    generateBatch,
    jobs,
    isGenerating,
    completedAnimations,
    error,
    reset,
    cancelAll,
  };
}
