import type { Severity, Service } from "../types";

/** Shared literal palette for Recharts/SVG, which cannot read CSS variables reliably. */
export const COLORS = {
  bg: "#080b0d",
  panel: "#0d1215",
  panel2: "#121a1e",
  border: "#1f2a30",
  borderStrong: "#33424a",
  text: "#e2e9e8",
  muted: "#93a4a8",
  faint: "#7f9297",
  accent: "#72e3a4",
  accentDim: "#3d7f5e",
  live: "#63d69b",
  low: "#6e93a8",
  medium: "#cfa84f",
  high: "#d3764b",
  critical: "#d94f4a",
  ssh: "#a78bd1",
  http: "#5fa8c7",
  grid: "#1f2a30",
  land: "#10181c",
  landStroke: "#2a3a42",
  ocean: "#090d0f",
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
