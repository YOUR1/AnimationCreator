"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { User, LoginCredentials, RegisterData, AuthState } from "@/types";

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });
  const router = useRouter();

  const fetchUser = useCallback(async () => {
    try {
      const user = await api.getCurrentUser();
      setState({
        user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  }, []);

  useEffect(() => {
    const hasToken = typeof window !== "undefined" && localStorage.getItem("access_token");
    if (hasToken) {
      fetchUser();
    } else {
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  }, [fetchUser]);

  const login = async (credentials: LoginCredentials) => {
    setState((prev) => ({ ...prev, isLoading: true }));
    try {
      const response = await api.login(credentials);
      setState({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
      });
      router.push("/");
      return response;
    } catch (error) {
      setState((prev) => ({ ...prev, isLoading: false }));
      throw error;
    }
  };

  const register = async (data: RegisterData) => {
    setState((prev) => ({ ...prev, isLoading: true }));
    try {
      const response = await api.register(data);
      setState({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
      });
      router.push("/");
      return response;
    } catch (error) {
      setState((prev) => ({ ...prev, isLoading: false }));
      throw error;
    }
  };

  const logout = async () => {
    setState((prev) => ({ ...prev, isLoading: true }));
    try {
      await api.logout();
    } finally {
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
      router.push("/login");
    }
  };

  const updateUser = (user: User) => {
    setState((prev) => ({ ...prev, user }));
  };

  return {
    ...state,
    login,
    register,
    logout,
    updateUser,
    refetch: fetchUser,
  };
}
