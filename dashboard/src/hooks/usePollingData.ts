import { useCallback, useEffect, useRef, useState } from "react";
import { toErrorMessage } from "../api/client";

export interface PollingResult<T> {
  data: T | null;
  error: string | null;
  isLoading: boolean;
  lastUpdated: number | null;
  refresh: () => void;
}

/**
 * REST polling with visibility pausing, exponential backoff, request abort and
 * stale-response protection. Restarts whenever `key` changes (window switch).
 */
export function usePollingData<T>(
  key: string,
  fetcher: (signal: AbortSignal) => Promise<T>,
  intervalMs: number,
): PollingResult<T> {
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let disposed = false;
    let timer: number | undefined;
    let inFlight: AbortController | null = null;
    let failures = 0;

    const clearTimer = () => {
      if (timer !== undefined) {
        window.clearTimeout(timer);
        timer = undefined;
      }
    };

    const schedule = (delay: number) => {
      clearTimer();
      if (disposed || document.hidden) return;
      timer = window.setTimeout(() => {
        void load();
      }, delay);
    };

    const load = async () => {
      clearTimer();
      inFlight?.abort();
      const controller = new AbortController();
      inFlight = controller;

      try {
        const next = await fetcherRef.current(controller.signal);
        if (disposed || controller.signal.aborted) return;
        failures = 0;
        setData(next);
        setError(null);
        setIsLoading(false);
        setLastUpdated(Date.now());
        schedule(intervalMs);
      } catch (caught) {
        if (disposed || controller.signal.aborted) return;
        failures += 1;
        setError(toErrorMessage(caught));
        setIsLoading(false);
        const backoff = Math.min(30_000, 1000 * 2 ** Math.min(failures, 5));
        schedule(backoff);
      }
    };

    const onVisibility = () => {
      if (document.hidden) {
        clearTimer();
        inFlight?.abort();
      } else {
        void load();
      }
    };

    setData(null);
    setError(null);
    setIsLoading(true);
    setLastUpdated(null);

    document.addEventListener("visibilitychange", onVisibility);
    void load();

    return () => {
      disposed = true;
      clearTimer();
      inFlight?.abort();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [key, intervalMs, nonce]);

  const refresh = useCallback(() => setNonce((value) => value + 1), []);

  return { data, error, isLoading, lastUpdated, refresh };
}

export function refreshInterval(): number {
  const configured = Number(import.meta.env.VITE_REFRESH_MS ?? 15_000);
  return Number.isFinite(configured) && configured >= 1000 ? configured : 15_000;
}
