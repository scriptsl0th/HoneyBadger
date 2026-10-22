import type { EventOut, WindowKey } from "../types";
import { techniqueLabel } from "./techniques";

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

const BYTE_UNITS = ["B", "KB", "MB", "GB", "TB"] as const;

/** 1234 -> "1.2k", 1_200_000 -> "1.2M". Stable across locales. */
export function compactNumber(value: number): string {
  if (!Number.isFinite(value)) return "—";
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (abs < 1000) return `${sign}${Math.round(abs)}`;

  const units = [
    { divisor: 1e9, suffix: "B" },
    { divisor: 1e6, suffix: "M" },
    { divisor: 1e3, suffix: "k" },
  ];

  for (let index = 0; index < units.length; index += 1) {
    const { divisor, suffix } = units[index];
    if (abs >= divisor) {
      const scaled = abs / divisor;
      const rounded =
        scaled >= 100 ? Math.round(scaled) : Math.round(scaled * 10) / 10;
      if (rounded >= 1000 && index > 0) {
        const next = units[index - 1];
        const promoted = abs / next.divisor;
        return `${sign}${trimDecimal(promoted)}${next.suffix}`;
      }
      return `${sign}${trimDecimal(rounded)}${suffix}`;
    }
  }
  return `${sign}${Math.round(abs)}`;
}

function trimDecimal(value: number): string {
  return value.toFixed(1).replace(/\.0$/, "");
}

/** 1536 -> "1.5 KB"; null -> "—". */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || !Number.isFinite(bytes)) {
    return "—";
  }
  if (bytes === 0) return "0 B";
  const sign = bytes < 0 ? "-" : "";
  const abs = Math.abs(bytes);
  const exponent = Math.min(
    BYTE_UNITS.length - 1,
    Math.floor(Math.log(abs) / Math.log(1024)),
  );
  const value = abs / 1024 ** exponent;
  const digits = value >= 100 || exponent === 0 ? 0 : 1;
  return `${sign}${value.toFixed(digits).replace(/\.0$/, "")} ${BYTE_UNITS[exponent]}`;
}

/** "just now", "42s ago", "7m ago", "3h ago", "2d ago", then a calendar date. */
export function relativeTime(
  iso: string | null | undefined,
  now: number = Date.now(),
): string {
  if (!iso) return "—";
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) return "—";
  const diff = now - timestamp;
  if (diff < 5_000) return "just now";

  if (diff < MINUTE) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < HOUR) return `${Math.floor(diff / MINUTE)}m ago`;
  if (diff < DAY) return `${Math.floor(diff / HOUR)}h ago`;
  if (diff < 30 * DAY) return `${Math.floor(diff / DAY)}d ago`;

  return new Date(timestamp).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Local wall-clock time with seconds, used by the live feed. */
export function formatClock(iso: string | null | undefined): string {
  if (!iso) return "—";
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) return "—";
  return new Date(timestamp).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function formatExact(iso: string | null | undefined): string {
  if (!iso) return "—";
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) return "—";
  return new Date(timestamp).toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZoneName: "short",
  });
}

/** Axis label for a timeseries bucket. */
export function formatBucketLabel(iso: string, window: WindowKey): string {
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) return "";
  const date = new Date(timestamp);
  if (window === "7d") {
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
  return date.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/** Percentage change, or null when there is no meaningful baseline. */
export function pctChange(
  current: number,
  previous: number,
): number | null {
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous <= 0) {
    return null;
  }
  return Math.round(((current - previous) / previous) * 1000) / 10;
}

/** Shortens a hash without changing the leading algorithm prefix. */
export function shortHash(
  hash: string | null | undefined,
  head = 10,
  tail = 4,
): string {
  if (!hash) return "—";
  if (hash.length <= head + tail + 1) return hash;
  return `${hash.slice(0, head)}…${hash.slice(-tail)}`;
}

export function truncate(value: string, max = 48): string {
  if (value.length <= max) return value;
  return `${value.slice(0, Math.max(0, max - 1))}…`;
}

/**
 * One-line plain-text description of an event. Attacker-controlled strings are
 * returned verbatim (never interpreted as HTML); the UI renders them as text.
 */
export function eventSummary(event: EventOut): string {
  const username = event.login_info?.username;
  const path = event.http_path;
  const method = event.http_method ?? "HTTP";

  switch (event.technique_id) {
    case "T1110":
    case "T1110.004": {
      const proto = event.service === "ssh" ? "SSH" : "HTTP";
      const label =
        event.technique_id === "T1110.004" ? "credential stuffing" : "login attempt";
      return `${proto} ${label}${username ? ` as ${username}` : ""}`;
    }
    case "T1595":
      return path ? `Scanned ${method} ${path}` : "Active scanning";
    case "T1190":
      return path ? `Exploit attempt: ${path}` : "Exploit attempt on public service";
    case "T1105":
      return event.payload_url
        ? `Ingress transfer: ${event.payload_url}`
        : "Ingress tool transfer";
    case "T1059":
      return event.command
        ? `Executed: ${event.command}`
        : "Command and scripting interpreter";
    case "T1078":
      return `Valid account use${username ? `: ${username}` : ""}`;
    default:
      if (path) return `${method} ${path}`;
      if (event.command) return `Command: ${event.command}`;
      if (event.payload_url) return `Payload: ${event.payload_url}`;
      return "Unclassified event";
  }
}

/** Compact subject used in the feed's final column. */
export function eventSubtitle(event: EventOut): string {
  if (event.technique_id) return techniqueLabel(event.technique_id);
  if (event.http_status_code) return `HTTP ${event.http_status_code}`;
  return event.service.toUpperCase();
}
