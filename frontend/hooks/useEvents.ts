import { useState, useEffect, useCallback } from 'react';
import {
  useEventsContext,
  type SSEEvent,
  type EventType,
  type CreditUpdateData,
  type GenerationUpdateData,
  type CharacterCreatedData,
  type AnimationCreatedData,
} from '@/contexts/events-context';

/**
 * Hook to subscribe to all SSE events
 */
export function useEvents() {
  const { events, isConnected, subscribeAll } = useEventsContext();
  const [latestEvent, setLatestEvent] = useState<SSEEvent | null>(null);

  useEffect(() => {
    const unsubscribe = subscribeAll((event) => {
      setLatestEvent(event);
    });

    return unsubscribe;
  }, [subscribeAll]);

  return {
    events,
    latestEvent,
    isConnected,
  };
}

/**
 * Hook to subscribe to specific event types
 */
export function useEventSubscription<T = unknown>(eventType: EventType) {
  const { isConnected, subscribe } = useEventsContext();
  const [lastEvent, setLastEvent] = useState<SSEEvent<T> | null>(null);

  useEffect(() => {
    const unsubscribe = subscribe<T>(eventType, (event) => {
      setLastEvent(event);
    });

    return unsubscribe;
  }, [eventType, subscribe]);

  return {
    lastEvent,
    isConnected,
  };
}

/**
 * Hook for real-time credit balance updates
 */
export function useCreditUpdates() {
  const { isConnected, subscribe } = useEventsContext();
  const [creditBalance, setCreditBalance] = useState<number | null>(null);
  const [lastChange, setLastChange] = useState<{ amount: number; reason?: string } | null>(null);

  useEffect(() => {
    const unsubscribe = subscribe<CreditUpdateData>('credit_update', (event) => {
      setCreditBalance(event.data.balance);
      setLastChange({
        amount: event.data.change,
        reason: event.data.reason,
      });
    });

    return unsubscribe;
  }, [subscribe]);

  return {
    creditBalance,
    lastChange,
    isConnected,
  };
}

/**
 * Hook for real-time generation status updates
 */
export function useGenerationUpdates() {
  const { isConnected, subscribe } = useEventsContext();
  const [generations, setGenerations] = useState<Map<number, GenerationUpdateData>>(new Map());

  useEffect(() => {
    const unsubscribe = subscribe<GenerationUpdateData>('generation_update', (event) => {
      setGenerations((prev) => {
        const newMap = new Map(prev);
        newMap.set(event.data.id, event.data);
        return newMap;
      });
    });

    return unsubscribe;
  }, [subscribe]);

  const getGeneration = useCallback(
    (id: number) => {
      return generations.get(id) || null;
    },
    [generations]
  );

  const clearGeneration = useCallback((id: number) => {
    setGenerations((prev) => {
      const newMap = new Map(prev);
      newMap.delete(id);
      return newMap;
    });
  }, []);

  return {
    generations: Array.from(generations.values()),
    getGeneration,
    clearGeneration,
    isConnected,
  };
}

/**
 * Hook for tracking a specific generation by ID
 */
export function useGenerationStatus(generationId: number | null) {
  const { isConnected, subscribe } = useEventsContext();
  const [status, setStatus] = useState<GenerationUpdateData | null>(null);

  useEffect(() => {
    if (generationId === null) {
      setStatus(null);
      return;
    }

    const unsubscribe = subscribe<GenerationUpdateData>('generation_update', (event) => {
      if (event.data.id === generationId) {
        setStatus(event.data);
      }
    });

    return unsubscribe;
  }, [generationId, subscribe]);

  return {
    status,
    isConnected,
  };
}

/**
 * Hook for new character creation notifications
 */
export function useCharacterCreated(onCreated?: (character: CharacterCreatedData) => void) {
  const { isConnected, subscribe } = useEventsContext();
  const [lastCreated, setLastCreated] = useState<CharacterCreatedData | null>(null);

  useEffect(() => {
    const unsubscribe = subscribe<CharacterCreatedData>('character_created', (event) => {
      setLastCreated(event.data);
      onCreated?.(event.data);
    });

    return unsubscribe;
  }, [subscribe, onCreated]);

  return {
    lastCreated,
    isConnected,
  };
}

/**
 * Hook for new animation creation notifications
 */
export function useAnimationCreated(onCreated?: (animation: AnimationCreatedData) => void) {
  const { isConnected, subscribe } = useEventsContext();
  const [lastCreated, setLastCreated] = useState<AnimationCreatedData | null>(null);

  useEffect(() => {
    const unsubscribe = subscribe<AnimationCreatedData>('animation_created', (event) => {
      setLastCreated(event.data);
      onCreated?.(event.data);
    });

    return unsubscribe;
  }, [subscribe, onCreated]);

  return {
    lastCreated,
    isConnected,
  };
}

// Re-export types for convenience
export type {
  SSEEvent,
  EventType,
  CreditUpdateData,
  GenerationUpdateData,
  CharacterCreatedData,
  AnimationCreatedData,
} from '@/contexts/events-context';
