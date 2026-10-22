import type { Severity, Service } from "../types";

/** Shared literal palette for Recharts/SVG, which cannot read CSS variables reliably. */
export const COLORS = {
  bg: "#0b1220",
  panel: "#111a2b",
  panel2: "#0f1728",
  border: "#1f2b45",
  text: "#e6edf7",
  muted: "#8fa3bf",
  low: "#38bdf8",
  medium: "#f59e0b",
  high: "#f97316",
  critical: "#ef4444",
  ssh: "#8b5cf6",
  http: "#06b6d4",
  grid: "#1f2b45",
} as const;

export const SEVERITY_SERIES: ReadonlyArray<{
  key: Severity;
  label: string;
  color: string;
}> = [
  { key: "low", label: "Low", color: COLORS.low },
  { key: "medium", label: "Medium", color: COLORS.medium },
  { key: "high", label: "High", color: COLORS.high },
  { key: "critical", label: "Critical", color: COLORS.critical },
];

export const SERVICE_SERIES: ReadonlyArray<{
  key: Service;
  label: string;
  color: string;
}> = [
  { key: "ssh", label: "SSH", color: COLORS.ssh },
  { key: "http", label: "HTTP", color: COLORS.http },
];

export function serviceColor(service: Service): string {
  return service === "ssh" ? COLORS.ssh : COLORS.http;
}

export function serviceLabel(service: Service): string {
  return service === "ssh" ? "SSH" : "HTTP";
}
