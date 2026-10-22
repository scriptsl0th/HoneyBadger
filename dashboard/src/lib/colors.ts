import type { Severity, Service } from "../types";

/** Shared literal palette for Recharts/SVG, which cannot read CSS variables reliably. */
export const COLORS = {
  bg: "#0b0c0a",
  panel: "#121410",
  panel2: "#171a15",
  border: "#272b23",
  borderStrong: "#3b4136",
  text: "#e9e6d9",
  muted: "#9b9e8e",
  faint: "#828675",
  accent: "#d9a441",
  accentDim: "#8a6a2b",
  live: "#93ae79",
  low: "#7ba39a",
  medium: "#d9a441",
  high: "#d1794d",
  critical: "#cb4b43",
  ssh: "#b3a5ce",
  http: "#86a6bd",
  grid: "#272b23",
  land: "#181b16",
  landStroke: "#30352b",
  ocean: "#0d0f0c",
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
