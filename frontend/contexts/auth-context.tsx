'use client';

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import type { User, LoginCredentials, RegisterData, CreditBalance } from '@/types';
import { EventsProvider } from '@/contexts/events-context';

interface AuthContextType {
  user: User | null;
  credits: CreditBalance | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  refreshCredits: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [credits, setCredits] = useState<CreditBalance | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    try {
      const userData = await api.getCurrentUser();
      setUser(userData);
    } catch {
      setUser(null);
      api.clearTokens();
    }
  }, []);

  const refreshCredits = useCallback(async () => {
    try {
      const creditData = await api.getCreditBalance();
      setCredits(creditData);
    } catch {
      setCredits(null);
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      // Reload tokens from cookies/localStorage (for OAuth redirect flow)
      api.loadTokens();

      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
      if (token) {
        await refreshUser();
        await refreshCredits();
      }
      setIsLoading(false);
    };
    initAuth();
  }, [refreshUser, refreshCredits]);

  const login = async (credentials: LoginCredentials) => {
    const response = await api.login(credentials);
    setUser(response.user);
    await refreshCredits();
    router.push('/dashboard');
  };

  const register = async (data: RegisterData) => {
    const response = await api.register(data);
    setUser(response.user);
    await refreshCredits();
    router.push('/dashboard');
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
    setCredits(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        credits,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshUser,
        refreshCredits,
      }}
    >
      <EventsProvider isAuthenticated={!!user}>
        {children}
      </EventsProvider>
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
