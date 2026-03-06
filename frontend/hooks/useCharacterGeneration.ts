'use client';

import { useState, useCallback } from 'react';
import api from '@/lib/api';
import { useJobProgress } from './useJobProgress';
import type { Generation, Character, GenerationStatus } from '@/types';

interface CharacterGenerationParams {
  name: string;
  prompt: string;
  style: string;
  description?: string;
}

interface UseCharacterGenerationReturn {
  generate: (params: CharacterGenerationParams) => Promise<void>;
  isGenerating: boolean;
  status: GenerationStatus | null;
  progress: number;
  character: Character | null;
  error: string | null;
  reset: () => void;
  generation: Generation | null;
}

export function useCharacterGeneration(): UseCharacterGenerationReturn {
  const [generation, setGeneration] = useState<Generation | null>(null);
  const [character, setCharacter] = useState<Character | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    status,
    progress,
    error: progressError,
    startTracking,
    reset: resetProgress,
  } = useJobProgress({
    onComplete: (data) => {
      if (data.result) {
        setCharacter(data.result as Character);
      }
    },
    onError: (err) => {
      setError(err.message);
    },
  });

  const generate = useCallback(async (params: CharacterGenerationParams) => {
    setIsStarting(true);
    setError(null);
    setCharacter(null);

    try {
      const gen = await api.createCharacter({
        name: params.name,
        description: params.description,
        style: params.style,
        prompt: params.prompt,
      } as Parameters<typeof api.createCharacter>[0]);

      setGeneration(gen);
      startTracking(gen.id);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start generation';
      setError(errorMessage);
    } finally {
      setIsStarting(false);
    }
  }, [startTracking]);

  const reset = useCallback(() => {
    setGeneration(null);
    setCharacter(null);
    setError(null);
    resetProgress();
  }, [resetProgress]);

  const isGenerating = isStarting || (status !== null && status !== 'completed' && status !== 'failed');

  return {
    generate,
    isGenerating,
    status,
    progress,
    character,
    error: error || progressError,
    reset,
    generation,
  };
}
