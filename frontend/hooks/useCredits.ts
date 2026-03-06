"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { CreditBalance } from "@/types";

export function useCredits() {
  const [credits, setCredits] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCredits = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const balance: CreditBalance = await api.getCreditBalance();
      setCredits(balance.credits);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch credits");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const hasToken = typeof window !== "undefined" && localStorage.getItem("access_token");
    if (hasToken) {
      fetchCredits();
    } else {
      setIsLoading(false);
    }
  }, [fetchCredits]);

  const refetch = useCallback(() => {
    fetchCredits();
  }, [fetchCredits]);

  return {
    credits,
    isLoading,
    error,
    refetch,
  };
}
