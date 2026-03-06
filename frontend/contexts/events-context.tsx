'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from 'react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3131';

// Event types that can be received from the SSE endpoint
export type EventType =
  | 'credit_update'
  | 'generation_update'
  | 'character_created'
  | 'animation_created'
  | 'connection_established'
  | 'heartbeat';

export interface SSEEvent<T = unknown> {
  type: EventType;
  data: T;
  timestamp: string;
}

export interface CreditUpdateData {
  balance: number;
  change: number;
  reason?: string;
}

export interface GenerationUpdateData {
  id: number;
  type: 'character' | 'animation';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  result_id?: number;
  error?: string;
}

export interface CharacterCreatedData {
  id: number;
  name: string;
  image_url: string;
  thumbnail_url: string;
}

export interface AnimationCreatedData {
  id: number;
  character_id: number;
  name: string;
  type: string;
  video_url: string;
  thumbnail_url?: string;
}

type EventSubscriber<T = unknown> = (event: SSEEvent<T>) => void;

interface EventsContextType {
  isConnected: boolean;
  events: SSEEvent[];
  subscribe: <T = unknown>(eventType: EventType, callback: EventSubscriber<T>) => () => void;
  subscribeAll: (callback: EventSubscriber) => () => void;
}

const EventsContext = createContext<EventsContextType | undefined>(undefined);

interface EventsProviderProps {
  children: ReactNode;
  isAuthenticated: boolean;
}

const MAX_EVENTS_HISTORY = 100;
const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

export function EventsProvider({ children, isAuthenticated }: EventsProviderProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<SSEEvent[]>([]);

  const eventSourceRef = useRef<EventSource | null>(null);
  const subscribersRef = useRef<Map<EventType | '*', Set<EventSubscriber>>>(new Map());
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const dispatchEvent = useCallback((event: SSEEvent) => {
    // Add to events history
    setEvents((prev) => {
      const newEvents = [event, ...prev];
      return newEvents.slice(0, MAX_EVENTS_HISTORY);
    });

    // Notify type-specific subscribers
    const typeSubscribers = subscribersRef.current.get(event.type);
    if (typeSubscribers) {
      typeSubscribers.forEach((callback) => callback(event));
    }

    // Notify "all events" subscribers
    const allSubscribers = subscribersRef.current.get('*');
    if (allSubscribers) {
      allSubscribers.forEach((callback) => callback(event));
    }
  }, []);

  const connect = useCallback(() => {
    if (typeof window === 'undefined') return;

    const token = localStorage.getItem('access_token');
    if (!token) return;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Create new EventSource connection with auth token in URL
    const url = `${API_BASE_URL}/api/events/stream?token=${encodeURIComponent(token)}`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
    };

    eventSource.onmessage = (event) => {
      try {
        const parsedEvent = JSON.parse(event.data) as SSEEvent;
        dispatchEvent(parsedEvent);
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      eventSource.close();
      eventSourceRef.current = null;

      // Attempt reconnection with exponential backoff
      if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = RECONNECT_DELAY_MS * Math.pow(2, reconnectAttemptsRef.current);
        reconnectAttemptsRef.current += 1;

        reconnectTimeoutRef.current = setTimeout(() => {
          if (isAuthenticated) {
            connect();
          }
        }, delay);
      }
    };
  }, [isAuthenticated, dispatchEvent]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setIsConnected(false);
    reconnectAttemptsRef.current = 0;
  }, []);

  // Connect/disconnect based on authentication state
  useEffect(() => {
    if (isAuthenticated) {
      connect();
    } else {
      disconnect();
      setEvents([]);
    }

    return () => {
      disconnect();
    };
  }, [isAuthenticated, connect, disconnect]);

  const subscribe = useCallback(
    <T = unknown>(eventType: EventType, callback: EventSubscriber<T>): (() => void) => {
      if (!subscribersRef.current.has(eventType)) {
        subscribersRef.current.set(eventType, new Set());
      }

      const subscribers = subscribersRef.current.get(eventType)!;
      subscribers.add(callback as EventSubscriber);

      // Return unsubscribe function
      return () => {
        subscribers.delete(callback as EventSubscriber);
        if (subscribers.size === 0) {
          subscribersRef.current.delete(eventType);
        }
      };
    },
    []
  );

  const subscribeAll = useCallback((callback: EventSubscriber): (() => void) => {
    if (!subscribersRef.current.has('*')) {
      subscribersRef.current.set('*', new Set());
    }

    const subscribers = subscribersRef.current.get('*')!;
    subscribers.add(callback);

    return () => {
      subscribers.delete(callback);
      if (subscribers.size === 0) {
        subscribersRef.current.delete('*');
      }
    };
  }, []);

  return (
    <EventsContext.Provider
      value={{
        isConnected,
        events,
        subscribe,
        subscribeAll,
      }}
    >
      {children}
    </EventsContext.Provider>
  );
}

export function useEventsContext() {
  const context = useContext(EventsContext);
  if (context === undefined) {
    throw new Error('useEventsContext must be used within an EventsProvider');
  }
  return context;
}
