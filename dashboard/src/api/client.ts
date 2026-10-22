const RAW_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";
export const API_BASE = RAW_BASE.replace(/\/+$/, "");

export type ApiErrorKind = "network" | "timeout" | "http" | "parse" | "aborted";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | undefined;
  readonly detail: unknown;

  constructor(
    message: string,
    kind: ApiErrorKind = "network",
    status?: number,
    detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.detail = detail;
  }
}

export function toErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Unexpected error";
}

interface RequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}

/**
 * Typed JSON fetch with a 10 s timeout, response normalisation and stale-request
 * cancellation through the caller's AbortSignal.
 */
export async function apiGet<T>(
  path: string,
  { signal, timeoutMs = 10_000 }: RequestOptions = {},
): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;
  const timeout = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  const forwardAbort = () => controller.abort();
  signal?.addEventListener("abort", forwardAbort, { once: true });
  if (signal?.aborted) controller.abort();

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
      cache: "no-store",
    });

    if (!response.ok) {
      let detail = "";
      try {
        detail = (await response.text()).slice(0, 300);
      } catch {
        detail = "";
      }
      throw new ApiError(
        detail
          ? `API returned ${response.status}: ${detail}`
          : `API returned ${response.status} ${response.statusText}`.trim(),
        "http",
        response.status,
        detail,
      );
    }

    const text = await response.text();
    if (!text) return undefined as T;

    try {
      return JSON.parse(text) as T;
    } catch (error) {
      throw new ApiError("API returned malformed JSON", "parse", response.status, error);
    }
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (timedOut) {
      throw new ApiError("API request timed out after 10 seconds", "timeout");
    }
    if (signal?.aborted) {
      throw new ApiError("Request cancelled", "aborted");
    }
    throw new ApiError("Cannot reach the HoneyBadger API", "network", undefined, error);
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener("abort", forwardAbort);
  }
}

export function buildQuery(
  params: Record<string, string | number | null | undefined>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") continue;
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}
