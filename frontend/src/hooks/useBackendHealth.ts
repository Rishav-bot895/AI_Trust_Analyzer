"use client";

import { useCallback, useEffect, useState } from "react";
import { checkBackendHealth } from "../lib/api-client";

export type BackendHealthState = {
  isHealthy: boolean;
  isChecking: boolean;
};

const POLL_INTERVAL_MS = 3000;

export function useBackendHealth(enabled = true): BackendHealthState {
  const [isHealthy, setIsHealthy] = useState(false);
  const [isChecking, setIsChecking] = useState(enabled);

  const checkHealth = useCallback(async () => {
    setIsChecking(true);

    try {
      await checkBackendHealth();
      setIsHealthy(true);
    } catch {
      setIsHealthy(false);
    } finally {
      setIsChecking(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    let cancelled = false;

    const runCheck = async () => {
      setIsChecking(true);

      try {
        await checkBackendHealth();
        if (!cancelled) setIsHealthy(true);
      } catch {
        if (!cancelled) setIsHealthy(false);
      } finally {
        if (!cancelled) setIsChecking(false);
      }
    };

    const initialCheckId = window.setTimeout(() => {
      void runCheck();
    }, 0);

    return () => {
      cancelled = true;
      window.clearTimeout(initialCheckId);
    };
  }, [enabled]);

  useEffect(() => {
    if (!enabled || isHealthy) return;

    const intervalId = window.setInterval(() => {
      void checkHealth();
    }, POLL_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [checkHealth, enabled, isHealthy]);

  return { isHealthy, isChecking };
}
