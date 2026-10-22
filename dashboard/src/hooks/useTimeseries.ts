import { useCallback } from "react";
import { getTimeseries } from "../api/endpoints";
import type { Timeseries, WindowKey } from "../types";
import { refreshInterval, usePollingData } from "./usePollingData";

export function useTimeseries(
  windowKey: WindowKey,
  intervalMs: number = refreshInterval(),
) {
  const fetcher = useCallback(
    (signal: AbortSignal) => getTimeseries(windowKey, signal),
    [windowKey],
  );
  return usePollingData<Timeseries>(
    `timeseries:${windowKey}`,
    fetcher,
    intervalMs,
  );
}
