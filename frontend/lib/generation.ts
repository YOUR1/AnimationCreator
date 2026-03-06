import type {
  Generation,
  GenerationStatus,
  GenerationStatusResponse,
  Character,
  Animation,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3131';

// Helper to get auth token
const getAuthToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
};

// Helper for authenticated requests
async function authFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// Character Generation
export interface CreateCharacterParams {
  prompt: string;
  style: string;
  name?: string;
  description?: string;
  negativePrompt?: string;
}

export async function createCharacter(params: CreateCharacterParams): Promise<Generation> {
  return authFetch<Generation>('/api/generate/character', {
    method: 'POST',
    body: JSON.stringify({
      prompt: params.prompt,
      style: params.style,
      name: params.name,
      description: params.description,
      negative_prompt: params.negativePrompt,
    }),
  });
}

// Animation Generation
export interface CreateAnimationsParams {
  characterId: string;
  states: string[];
  options?: {
    duration?: number;
    fps?: number;
    format?: 'mp4' | 'gif' | 'webm';
  };
}

export async function createAnimations(params: CreateAnimationsParams): Promise<Generation[]> {
  const { characterId, states, options } = params;

  // Create a generation for each animation state
  const generations = await Promise.all(
    states.map((state) =>
      authFetch<Generation>('/api/generate/animations', {
        method: 'POST',
        body: JSON.stringify({
          character_id: characterId,
          animation_type: state,
          duration: options?.duration,
          fps: options?.fps,
          format: options?.format,
        }),
      })
    )
  );

  return generations;
}

// Single animation generation
export interface CreateSingleAnimationParams {
  characterId: string;
  type: string;
  name: string;
  prompt?: string;
  duration?: number;
  fps?: number;
  format?: 'mp4' | 'gif' | 'webm';
}

export async function createAnimation(params: CreateSingleAnimationParams): Promise<Generation> {
  return authFetch<Generation>('/api/generate/animation', {
    method: 'POST',
    body: JSON.stringify({
      character_id: params.characterId,
      type: params.type,
      name: params.name,
      prompt: params.prompt,
      duration: params.duration,
      fps: params.fps,
      format: params.format,
    }),
  });
}

// Job Status
export async function getJobStatus(jobId: string): Promise<GenerationStatusResponse> {
  return authFetch<GenerationStatusResponse>(`/api/generate/${jobId}/status`);
}

// SSE Stream for job progress
export interface JobProgressData {
  generation: Generation;
  result?: Character | Animation;
}

export interface StreamOptions {
  onProgress?: (data: JobProgressData) => void;
  onComplete?: (data: JobProgressData) => void;
  onError?: (error: Error) => void;
}

export function streamJobProgress(
  jobId: string,
  options: StreamOptions
): () => void {
  const { onProgress, onComplete, onError } = options;

  let eventSource: EventSource | null = null;
  let isAborted = false;

  const connect = () => {
    if (isAborted) return;

    const token = getAuthToken();
    const url = new URL(`${API_BASE_URL}/api/generate/${jobId}/stream`);
    if (token) {
      url.searchParams.set('token', token);
    }

    eventSource = new EventSource(url.toString());

    eventSource.onopen = () => {
      console.log(`SSE connected for job ${jobId}`);
    };

    eventSource.onmessage = (event) => {
      try {
        const data: JobProgressData = JSON.parse(event.data);
        onProgress?.(data);

        if (data.generation.status === 'completed') {
          onComplete?.(data);
          eventSource?.close();
        } else if (data.generation.status === 'failed') {
          const error = new Error(data.generation.error || 'Generation failed');
          onError?.(error);
          eventSource?.close();
        }
      } catch (e) {
        console.error('Failed to parse SSE data:', e);
      }
    };

    eventSource.onerror = (event) => {
      console.error('SSE error:', event);
      eventSource?.close();

      // Attempt reconnection after a delay if not completed
      if (!isAborted) {
        setTimeout(() => {
          connect();
        }, 2000);
      }
    };
  };

  connect();

  // Return cleanup function
  return () => {
    isAborted = true;
    eventSource?.close();
  };
}

// Polling-based job progress (fallback)
export function pollJobProgress(
  jobId: string,
  options: StreamOptions,
  intervalMs: number = 2000
): () => void {
  const { onProgress, onComplete, onError } = options;

  let isAborted = false;
  let timeoutId: NodeJS.Timeout | null = null;

  const poll = async () => {
    if (isAborted) return;

    try {
      const data = await getJobStatus(jobId);
      const progressData: JobProgressData = {
        generation: data.generation,
        result: data.result,
      };

      onProgress?.(progressData);

      if (data.generation.status === 'completed') {
        onComplete?.(progressData);
        return;
      } else if (data.generation.status === 'failed') {
        const error = new Error(data.generation.error || 'Generation failed');
        onError?.(error);
        return;
      }

      // Continue polling
      timeoutId = setTimeout(poll, intervalMs);
    } catch (e) {
      const error = e instanceof Error ? e : new Error('Polling failed');
      onError?.(error);
    }
  };

  poll();

  // Return cleanup function
  return () => {
    isAborted = true;
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  };
}

// Utility to track multiple jobs
export interface MultiJobTracker {
  addJob: (jobId: string) => void;
  removeJob: (jobId: string) => void;
  getStatus: (jobId: string) => GenerationStatus | undefined;
  getProgress: (jobId: string) => number;
  getAllStatuses: () => Map<string, GenerationStatus>;
  cleanup: () => void;
}

export function createMultiJobTracker(
  onUpdate?: (jobId: string, data: JobProgressData) => void
): MultiJobTracker {
  const jobs = new Map<string, { status: GenerationStatus; progress: number; cleanup: () => void }>();

  const addJob = (jobId: string) => {
    if (jobs.has(jobId)) return;

    const cleanup = streamJobProgress(jobId, {
      onProgress: (data) => {
        const existing = jobs.get(jobId);
        if (existing) {
          existing.status = data.generation.status;
          existing.progress = data.generation.progress;
        }
        onUpdate?.(jobId, data);
      },
      onComplete: (data) => {
        const existing = jobs.get(jobId);
        if (existing) {
          existing.status = 'completed';
          existing.progress = 100;
        }
        onUpdate?.(jobId, data);
      },
      onError: () => {
        const existing = jobs.get(jobId);
        if (existing) {
          existing.status = 'failed';
        }
      },
    });

    jobs.set(jobId, { status: 'pending', progress: 0, cleanup });
  };

  const removeJob = (jobId: string) => {
    const job = jobs.get(jobId);
    if (job) {
      job.cleanup();
      jobs.delete(jobId);
    }
  };

  const getStatus = (jobId: string) => jobs.get(jobId)?.status;
  const getProgress = (jobId: string) => jobs.get(jobId)?.progress ?? 0;
  const getAllStatuses = () => new Map(Array.from(jobs.entries()).map(([id, j]) => [id, j.status]));

  const cleanup = () => {
    jobs.forEach((job) => job.cleanup());
    jobs.clear();
  };

  return {
    addJob,
    removeJob,
    getStatus,
    getProgress,
    getAllStatuses,
    cleanup,
  };
}
