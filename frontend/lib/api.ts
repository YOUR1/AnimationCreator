import type {
  User,
  AuthTokens,
  AuthResponse,
  LoginCredentials,
  RegisterData,
  CreditBalance,
  Transaction,
  Character,
  CharacterCreateRequest,
  Animation,
  AnimationCreateRequest,
  Generation,
  GenerationStatusResponse,
  Asset,
  CreditPack,
  CheckoutSession,
  PaginatedResponse,
  ApiError,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3131';

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    this.loadTokens();
  }

  loadTokens() {
    if (typeof window !== 'undefined') {
      // Try localStorage first
      this.accessToken = localStorage.getItem('access_token');
      this.refreshToken = localStorage.getItem('refresh_token');

      // If not in localStorage, check cookies (for OAuth redirect flow)
      if (!this.accessToken) {
        const cookies = document.cookie.split(';').reduce((acc, cookie) => {
          const [key, value] = cookie.trim().split('=');
          acc[key] = value;
          return acc;
        }, {} as Record<string, string>);

        if (cookies['access_token']) {
          this.accessToken = cookies['access_token'];
          this.refreshToken = cookies['refresh_token'] || null;
          // Sync to localStorage
          localStorage.setItem('access_token', this.accessToken);
          if (this.refreshToken) {
            localStorage.setItem('refresh_token', this.refreshToken);
          }
        }
      }
    }
  }

  setTokens(tokens: AuthTokens) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);
      // Also set cookies for middleware auth check
      document.cookie = `access_token=${tokens.access_token}; path=/; max-age=${60 * 60 * 24 * 7}`; // 7 days
      document.cookie = `refresh_token=${tokens.refresh_token}; path=/; max-age=${60 * 60 * 24 * 7}`;
    }
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      // Also clear cookies
      document.cookie = 'access_token=; path=/; max-age=0';
      document.cookie = 'refresh_token=; path=/; max-age=0';
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.accessToken) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401 && this.refreshToken) {
      // Try to refresh the token
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${this.accessToken}`;
        const retryResponse = await fetch(url, { ...options, headers });
        if (!retryResponse.ok) {
          const error: ApiError = await retryResponse.json();
          throw new Error(error.detail || 'Request failed');
        }
        return retryResponse.json();
      }
    }

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.detail || 'Request failed');
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  private async refreshAccessToken(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });

      if (!response.ok) {
        this.clearTokens();
        return false;
      }

      const tokens: AuthTokens = await response.json();
      this.setTokens(tokens);
      return true;
    } catch {
      this.clearTokens();
      return false;
    }
  }

  // Auth endpoints
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const backendResponse = await this.request<{
      access_token: string;
      refresh_token: string;
      token_type: string;
      expires_in: number;
      user: User;
    }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    const tokens = {
      access_token: backendResponse.access_token,
      refresh_token: backendResponse.refresh_token,
    };
    this.setTokens(tokens);
    return { user: backendResponse.user, tokens };
  }

  async register(data: RegisterData): Promise<AuthResponse> {
    const backendResponse = await this.request<{
      access_token: string;
      refresh_token: string;
      token_type: string;
      expires_in: number;
      user: User;
    }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    const tokens = {
      access_token: backendResponse.access_token,
      refresh_token: backendResponse.refresh_token,
    };
    this.setTokens(tokens);
    return { user: backendResponse.user, tokens };
  }

  async logout(): Promise<void> {
    try {
      await this.request<void>('/api/auth/logout', { method: 'POST' });
    } finally {
      this.clearTokens();
    }
  }

  async forgotPassword(email: string): Promise<void> {
    await this.request<void>('/api/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  }

  async resetPassword(token: string, password: string): Promise<void> {
    await this.request<void>('/api/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, password }),
    });
  }

  // User endpoints
  async getCurrentUser(): Promise<User> {
    return this.request<User>('/api/users/me');
  }

  async updateUser(data: Partial<User>): Promise<User> {
    return this.request<User>('/api/users/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async getCreditBalance(): Promise<CreditBalance> {
    const response = await this.request<{ balance: number; lifetime_purchased: number }>('/api/users/me/credits');
    return {
      credits: response.balance,
      last_updated: new Date().toISOString(),
    };
  }

  async getTransactionHistory(page = 1, pageSize = 20): Promise<PaginatedResponse<Transaction>> {
    // Backend uses /history endpoint which returns both transactions and generations
    const limit = pageSize;
    const offset = (page - 1) * pageSize;
    const response = await this.request<{
      transactions: Transaction[];
      generations: Array<{
        id: number;
        generation_type: string;
        credits_used: number;
        status: string;
        started_at: string | null;
        completed_at: string | null;
        created_at: string;
      }>;
    }>(`/api/users/me/history?limit=${limit}&offset=${offset}`);

    return {
      items: response.transactions,
      total: response.transactions.length,
      page,
      page_size: pageSize,
      total_pages: 1,
    };
  }

  async getGenerationHistory(limit = 50, offset = 0): Promise<{ transactions: Transaction[]; generations: Generation[] }> {
    const response = await this.request<{
      transactions: Array<{
        id: number;
        type: string;
        amount: number;
        description: string | null;
        created_at: string;
      }>;
      generations: Array<{
        id: number;
        generation_type: string;
        credits_used: number;
        status: string;
        started_at: string | null;
        completed_at: string | null;
        created_at: string;
      }>;
    }>(`/api/users/me/history?limit=${limit}&offset=${offset}`);

    // Transform backend response to match frontend Generation type
    const generations: Generation[] = response.generations.map((g) => ({
      id: String(g.id),
      user_id: '',
      type: g.generation_type as 'character' | 'animation',
      status: g.status as 'pending' | 'processing' | 'completed' | 'failed',
      progress: g.status === 'completed' ? 100 : g.status === 'processing' ? 50 : 0,
      created_at: g.created_at,
      updated_at: g.completed_at || g.created_at,
    }));

    return { transactions: response.transactions as unknown as Transaction[], generations };
  }

  // Character endpoints
  async getCharacters(
    page = 1,
    pageSize = 20,
    options?: { sortBy?: string; sortOrder?: 'asc' | 'desc'; style?: string }
  ): Promise<PaginatedResponse<Character>> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (options?.sortBy) params.append('sort_by', options.sortBy);
    if (options?.sortOrder) params.append('sort_order', options.sortOrder);
    if (options?.style) params.append('style', options.style);
    return this.request<PaginatedResponse<Character>>(`/api/characters?${params}`);
  }

  async getCharacter(id: string): Promise<Character> {
    return this.request<Character>(`/api/characters/${id}`);
  }

  async createCharacter(data: CharacterCreateRequest): Promise<Generation> {
    // Map frontend style values to backend style values
    const styleMapping: Record<string, string> = {
      anime: 'kawaii',
      cartoon: 'watercolor',
      realistic: 'realistic',
      pixel: 'pixel',
      '3d': 'pixar',
    };

    const mappedData = {
      ...data,
      style: styleMapping[data.style] || data.style,
    };

    return this.request<Generation>('/api/generate/character', {
      method: 'POST',
      body: JSON.stringify(mappedData),
    });
  }

  async deleteCharacter(id: string): Promise<void> {
    return this.request<void>(`/api/characters/${id}`, { method: 'DELETE' });
  }

  // Animation endpoints
  async getAnimations(
    page = 1,
    pageSize = 20,
    options?: { characterId?: string; sortBy?: string; sortOrder?: 'asc' | 'desc'; type?: string }
  ): Promise<PaginatedResponse<Animation>> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (options?.characterId) params.append('character_id', options.characterId);
    if (options?.sortBy) params.append('sort_by', options.sortBy);
    if (options?.sortOrder) params.append('sort_order', options.sortOrder);
    if (options?.type) params.append('type', options.type);
    return this.request<PaginatedResponse<Animation>>(`/api/animations?${params}`);
  }

  async getAnimation(id: string): Promise<Animation> {
    return this.request<Animation>(`/api/animations/${id}`);
  }

  async createAnimation(data: AnimationCreateRequest): Promise<Generation> {
    return this.request<Generation>('/api/generate/animations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteAnimation(id: string): Promise<void> {
    return this.request<void>(`/api/animations/${id}`, { method: 'DELETE' });
  }

  // Generation endpoints
  async getGenerationStatus(id: string): Promise<GenerationStatusResponse> {
    return this.request<GenerationStatusResponse>(`/api/generate/status/${id}`);
  }

  async streamGenerationStatus(id: string, onProgress: (data: GenerationStatusResponse) => void): Promise<void> {
    const eventSource = new EventSource(`${API_BASE_URL}/api/generate/stream/${id}`);

    return new Promise((resolve, reject) => {
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        onProgress(data);
        if (data.generation.status === 'completed' || data.generation.status === 'failed') {
          eventSource.close();
          resolve();
        }
      };
      eventSource.onerror = () => {
        eventSource.close();
        reject(new Error('Stream connection failed'));
      };
    });
  }

  async getPendingGenerations(): Promise<{
    generations: Array<{
      id: number;
      type: string;
      status: string;
      credits_used: number;
      created_at: string;
    }>;
  }> {
    return this.request('/api/generate/pending');
  }

  async cancelGeneration(id: number): Promise<{ message: string; credits_refunded: number }> {
    return this.request(`/api/generate/${id}`, { method: 'DELETE' });
  }

  // Asset endpoints
  async uploadAsset(file: File): Promise<Asset> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/assets/upload`, {
      method: 'POST',
      headers: this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {},
      body: formData,
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  async deleteAsset(id: string): Promise<void> {
    return this.request<void>(`/api/assets/${id}`, { method: 'DELETE' });
  }

  // Billing endpoints
  async getCreditPacks(): Promise<CreditPack[]> {
    const response = await this.request<{
      packs: Array<{
        id: string;
        name: string;
        description: string;
        credits: number;
        price_cents: number;
        price_dollars: number;
        price_per_credit: number;
      }>;
    }>('/api/billing/packs');
    return response.packs.map((pack) => ({
      id: pack.id,
      name: pack.name,
      credits: pack.credits,
      price: pack.price_dollars,
      currency: 'USD',
      popular: pack.id === 'medium',
    }));
  }

  async createCheckoutSession(packId: string): Promise<CheckoutSession> {
    const response = await this.request<{
      checkout_url: string;
      session_id: string;
    }>('/api/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ pack_id: packId }),
    });
    return {
      id: response.session_id,
      url: response.checkout_url,
    };
  }

  async getBillingPortalUrl(): Promise<{ url: string }> {
    const response = await this.request<{ portal_url: string }>('/api/billing/portal');
    return { url: response.portal_url };
  }
}

export const api = new ApiClient();
export default api;
