import type {
  EventListResponse,
  EventQuery,
  Health,
  Stats,
  Timeseries,
  WindowKey,
} from "../types";
import { apiGet, buildQuery } from "./client";

/** Mock mode is only enabled by an explicit VITE_API_MODE=mock. */
export const IS_MOCK = import.meta.env.VITE_API_MODE === "mock";

const loadMock = () => import("./mock");

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  if (IS_MOCK) return (await loadMock()).mockGetHealth();
  return apiGet<Health>("/health", { signal });
}

export async function getEvents(
  params: EventQuery = {},
  signal?: AbortSignal,
): Promise<EventListResponse> {
  if (IS_MOCK) return (await loadMock()).mockGetEvents(params);

  const query = buildQuery({
    limit: params.limit,
    service: params.service,
    severity: params.severity,
    technique: params.technique,
    since: params.since,
  });
  return apiGet<EventListResponse>(`/events${query}`, { signal });
}

export async function getStats(
  window: WindowKey,
  signal?: AbortSignal,
): Promise<Stats> {
  if (IS_MOCK) return (await loadMock()).mockGetStats(window);
  return apiGet<Stats>(`/stats${buildQuery({ window })}`, { signal });
}

export async function getTimeseries(
  window: WindowKey,
  signal?: AbortSignal,
): Promise<Timeseries> {
  if (IS_MOCK) return (await loadMock()).mockGetTimeseries(window);
  return apiGet<Timeseries>(`/stats/timeseries${buildQuery({ window })}`, { signal });
}
