import { useCallback } from "react";
import { getStats } from "../api/endpoints";
import type { Stats, WindowKey } from "../types";
import { refreshInterval, usePollingData } from "./usePollingData";

export function useStats(
  windowKey: WindowKey,
  intervalMs: number = refreshInterval(),
) {
  const fetcher = useCallback(
    (signal: AbortSignal) => getStats(windowKey, signal),
    [windowKey],
  );
  return usePollingData<Stats>(`stats:${windowKey}`, fetcher, intervalMs);
}
