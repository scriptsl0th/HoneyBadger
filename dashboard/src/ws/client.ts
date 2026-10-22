import type { EventOut } from "../types";

export type LiveStatus = "connecting" | "live" | "reconnecting" | "polling";

export interface LiveCallbacks {
  onEvent: (event: EventOut) => void;
  onStatus: (status: LiveStatus, attempt?: number) => void;
  onHello?: (serverTime: string) => void;
}

export interface LiveConnection {
  close: () => void;
}

const MOCK = import.meta.env.VITE_API_MODE === "mock";
const MAX_BACKOFF = 30_000;
const HEARTBEAT_TIMEOUT = 50_000;

function wsPath(): string {
  const raw = import.meta.env.VITE_WS_PATH || "/ws/events";
  return raw.startsWith("/") ? raw : `/${raw}`;
}

function resolveWsUrl(): string {
  const apiBase = import.meta.env.VITE_API_BASE_URL || "/api";
  if (/^https?:\/\//i.test(apiBase)) {
    try {
      const parsed = new URL(apiBase);
      const protocol = parsed.protocol === "https:" ? "wss:" : "ws:";
      return `${protocol}//${parsed.host}${wsPath()}`;
    } catch {
      /* fall through to same-origin */
    }
  }
  const protocol =
    typeof window !== "undefined" && window.location.protocol === "https:"
      ? "wss:"
      : "ws:";
  const host =
    typeof window !== "undefined" ? window.location.host : "localhost:5173";
  return `${protocol}//${host}${wsPath()}`;
}

function isEventOut(value: unknown): value is EventOut {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return (
    (candidate.service === "ssh" || candidate.service === "http") &&
    typeof candidate.source_ip === "string" &&
    typeof candidate.timestamp === "string"
  );
}

/**
 * Live event connection. Mock mode subscribes to the local synthesiser; API mode
 * uses `/ws/events` with exponential backoff + jitter and a stale-socket watchdog.
 */
export function connectLive(callbacks: LiveCallbacks): LiveConnection {
  if (MOCK) {
    let closed = false;
    let unsubscribe = () => {};
    callbacks.onStatus("connecting", 0);
    void import("../api/mock")
      .then((mock) => {
        if (closed) return;
        callbacks.onHello?.(new Date().toISOString());
        callbacks.onStatus("live", 0);
        unsubscribe = mock.subscribeMockEvents(callbacks.onEvent);
      })
      .catch(() => {
        if (!closed) callbacks.onStatus("polling", 0);
      });

    return {
      close: () => {
        closed = true;
        unsubscribe();
      },
    };
  }

  let socket: WebSocket | null = null;
  let closed = false;
  let attempt = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  let lastMessageAt = Date.now();

  const clearTimers = () => {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (heartbeatTimer !== null) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  };

  const scheduleReconnect = () => {
    if (closed) return;
    const status: LiveStatus = attempt >= 3 ? "polling" : "reconnecting";
    callbacks.onStatus(status, attempt);
    const base = Math.min(MAX_BACKOFF, 1000 * 2 ** Math.min(attempt, 5));
    const delay = Math.round(base * (0.8 + Math.random() * 0.4));
    attempt += 1;
    reconnectTimer = setTimeout(open, delay);
  };

  const startHeartbeat = () => {
    if (heartbeatTimer !== null) clearInterval(heartbeatTimer);
    lastMessageAt = Date.now();
    heartbeatTimer = setInterval(() => {
      if (closed || !socket || socket.readyState !== WebSocket.OPEN) return;
      if (Date.now() - lastMessageAt > HEARTBEAT_TIMEOUT) {
        // Quiet socket: force a clean reconnect. REST polling covers the gap.
        socket.close(4000, "heartbeat timeout");
      }
    }, 15_000);
  };

  function open() {
    if (closed) return;
    clearTimers();
    callbacks.onStatus(attempt === 0 ? "connecting" : "reconnecting", attempt);

    let next: WebSocket;
    try {
      next = new WebSocket(resolveWsUrl());
    } catch {
      scheduleReconnect();
      return;
    }
    socket = next;

    next.onopen = () => {
      if (closed) {
        next.close();
        return;
      }
      attempt = 0;
      lastMessageAt = Date.now();
      callbacks.onStatus("live", 0);
      startHeartbeat();
    };

    next.onmessage = (message) => {
      lastMessageAt = Date.now();
      if (typeof message.data !== "string") return;
      let payload: unknown;
      try {
        payload = JSON.parse(message.data);
      } catch {
        return;
      }
      if (!payload || typeof payload !== "object") return;
      const data = payload as Record<string, unknown>;
      if (data.type === "hello" && typeof data.server_time === "string") {
        callbacks.onHello?.(data.server_time);
        return;
      }
      if (data.type === "event" && isEventOut(data.event)) {
        callbacks.onEvent(data.event);
      }
      // Unknown message types are deliberately ignored.
    };

    next.onerror = () => {
      // The close event that follows drives the reconnect.
    };

    next.onclose = () => {
      if (socket === next) socket = null;
      if (heartbeatTimer !== null) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
      }
      if (closed) return;
      scheduleReconnect();
    };
  }

  open();

  return {
    close: () => {
      closed = true;
      clearTimers();
      if (socket) {
        socket.onclose = null;
        socket.close(1000, "client closed");
        socket = null;
      }
    },
  };
}
