import { useCallback, useEffect, useRef, useState } from "react";
import { toErrorMessage } from "../api/client";
import { getEvents } from "../api/endpoints";
import { mergeEvents } from "../lib/events";
import type { EventOut } from "../types";
import { connectLive, type LiveStatus } from "../ws/client";

const FEED_CAP = 500;
const POLL_FALLBACK_MS = 10_000;

interface Options {
  paused?: boolean;
}

export interface LiveEventsResult {
  events: EventOut[];
  status: LiveStatus;
  attempt: number;
  pendingCount: number;
  error: string | null;
  isLoading: boolean;
  refresh: () => void;
}

/**
 * Live feed: REST seed + WebSocket stream, with a 10 s `/events?since=` poll while
 * the socket is down. Paused feed keeps a bounded pending queue, then flushes.
 */
export function useLiveEvents({ paused = false }: Options = {}): LiveEventsResult {
  const [events, setEvents] = useState<EventOut[]>([]);
  const [status, setStatus] = useState<LiveStatus>("connecting");
  const [attempt, setAttempt] = useState(0);
  const [seedError, setSeedError] = useState<string | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [seeded, setSeeded] = useState(false);
  const [seedNonce, setSeedNonce] = useState(0);

  const pausedRef = useRef(paused);
  pausedRef.current = paused;
  const pendingRef = useRef<EventOut[]>([]);
  const lastTimestampRef = useRef<string>(new Date(0).toISOString());

  const ingest = useCallback((incoming: EventOut | EventOut[]) => {
    const batch = Array.isArray(incoming) ? incoming : [incoming];
    if (batch.length === 0) return;

    for (const event of batch) {
      if (Date.parse(event.timestamp) > Date.parse(lastTimestampRef.current)) {
        lastTimestampRef.current = event.timestamp;
      }
    }

    if (pausedRef.current) {
      pendingRef.current = mergeEvents(pendingRef.current, batch, FEED_CAP);
      setPendingCount(pendingRef.current.length);
      return;
    }

    setEvents((current) => mergeEvents(current, batch, FEED_CAP));
  }, []);

  useEffect(() => {
    pausedRef.current = paused;
    if (!paused && pendingRef.current.length > 0) {
      const batch = pendingRef.current;
      pendingRef.current = [];
      setPendingCount(0);
      setEvents((current) => mergeEvents(current, batch, FEED_CAP));
    }
  }, [paused]);

  useEffect(() => {
    const controller = new AbortController();
    setSeedError(null);
    getEvents({ limit: 100 }, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;
        ingest(response.items);
        setSeedError(null);
        setSeeded(true);
      })
      .catch((caught) => {
        if (controller.signal.aborted) return;
        setSeedError(toErrorMessage(caught));
        setSeeded(true);
      });
    return () => controller.abort();
  }, [ingest, seedNonce]);

  useEffect(() => {
    const connection = connectLive({
      onEvent: ingest,
      onStatus: (next, nextAttempt) => {
        setStatus(next);
        setAttempt(nextAttempt ?? 0);
      },
    });
    return () => connection.close();
  }, [ingest]);

  useEffect(() => {
    if (status === "live") return;

    let cancelled = false;
    let timer: number | undefined;
    let controller: AbortController | null = null;

    const poll = async () => {
      controller?.abort();
      controller = new AbortController();
      try {
        const response = await getEvents(
          { limit: 100, since: lastTimestampRef.current },
          controller.signal,
        );
        if (!cancelled) {
          ingest(response.items);
          setSeedError(null);
        }
      } catch {
        // The socket keeps retrying; a failed fallback poll stays silent.
      } finally {
        if (!cancelled) timer = window.setTimeout(poll, POLL_FALLBACK_MS);
      }
    };

    void poll();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
      controller?.abort();
    };
  }, [status, ingest]);

  return {
    events,
    status,
    attempt,
    pendingCount,
    error: seedError,
    isLoading: !seeded && events.length === 0,
    refresh: () => setSeedNonce((value) => value + 1),
  };
}
