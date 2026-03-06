// User types
export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  avatar_url?: string;
  credits: number;
  created_at: string;
  updated_at: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  name?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

// Credit types
export interface CreditBalance {
  credits: number;
  last_updated: string;
}

export interface Transaction {
  id: string;
  user_id: string;
  amount: number;
  type: TransactionType;
  description: string;
  created_at: string;
}

export type TransactionType = "purchase" | "usage" | "refund" | "bonus";

// Character types
export interface Character {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  style?: string;
  prompt?: string;
  image_url: string;
  thumbnail_url: string;
  status: CharacterStatus;
  created_at: string;
  updated_at: string;
}

export type CharacterStatus = "pending" | "processing" | "completed" | "failed";

export interface CharacterCreateRequest {
  name: string;
  description?: string;
  style: string;
  prompt: string;
}

// Animation types
export interface Animation {
  id: string;
  character_id: string;
  user_id: string;
  name: string;
  type: AnimationType;
  video_url?: string;
  gif_url?: string;
  thumbnail_url?: string;
  status: AnimationStatus;
  duration: number;
  created_at: string;
  updated_at: string;
}

export type AnimationType = "idle" | "walk" | "run" | "jump" | "attack" | "dancing" | "sad" | "excited" | "custom";

export type AnimationStatus = "pending" | "processing" | "completed" | "failed";

export type AspectRatio = "1:1" | "16:9" | "9:16";

export type SpecialFx = "hug" | "kiss" | "heart_gesture" | "squish" | "expansion";

export interface AnimationCreateRequest {
  character_id: string;
  type: AnimationType;
  name: string;
  prompt?: string;
  duration?: number;
  aspect_ratio?: AspectRatio;
  negative_prompt?: string;
  cfg_scale?: number;
  special_fx?: SpecialFx;
}

// Generation types
export interface Generation {
  id: string;
  user_id: string;
  type: GenerationType;
  status: GenerationStatus;
  progress: number;
  result_id?: string;
  error?: string;
  created_at: string;
  updated_at: string;
}

export type GenerationType = "character" | "animation";

export type GenerationStatus = "pending" | "processing" | "completed" | "failed";

export interface GenerationStatusResponse {
  generation: Generation;
  result?: Character | Animation;
}

// Asset types
export interface Asset {
  id: string;
  user_id: string;
  filename: string;
  url: string;
  content_type: string;
  size: number;
  created_at: string;
}

// Credit pack types
export interface CreditPack {
  id: string;
  name: string;
  credits: number;
  price: number;
  currency: string;
  popular?: boolean;
}

export interface CheckoutSession {
  id: string;
  url: string;
}

// API types
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface ApiError {
  detail: string;
  code?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

// OAuth providers
export type OAuthProvider = "google" | "github" | "discord";
