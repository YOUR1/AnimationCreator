import { api } from "./api";
import type { User, LoginCredentials, RegisterData, AuthResponse, OAuthProvider } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3131";

export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  return api.login(credentials);
}

export async function register(data: RegisterData): Promise<AuthResponse> {
  return api.register(data);
}

export async function logout(): Promise<void> {
  return api.logout();
}

export async function forgotPassword(email: string): Promise<void> {
  return api.forgotPassword(email);
}

export async function resetPassword(token: string, password: string): Promise<void> {
  return api.resetPassword(token, password);
}

export async function getCurrentUser(): Promise<User> {
  return api.getCurrentUser();
}

export async function getSession(): Promise<User | null> {
  try {
    const user = await api.getCurrentUser();
    return user;
  } catch {
    return null;
  }
}

export function getOAuthUrl(provider: OAuthProvider): string {
  return `${API_BASE_URL}/api/auth/oauth/${provider}/authorize`;
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("access_token");
}
