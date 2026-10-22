import type { Severity } from "../types";
import { COLORS } from "./colors";

export const SEVERITY_ORDER: readonly Severity[] = [
  "low",
  "medium",
  "high",
  "critical",
] as const;

export const SEVERITY_RANK: Record<Severity, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};

export const SEVERITY_COLORS: Record<Severity, string> = {
  low: COLORS.low,
  medium: COLORS.medium,
  high: COLORS.high,
  critical: COLORS.critical,
};

export const SEVERITY_LABELS: Record<Severity, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

/**
 * Lighter tints for 9px labels. The base severity colours are tuned as chart
 * fills; at label size they would fall under 4.5:1 on the ink surface.
 */
export const SEVERITY_TEXT_COLORS: Record<Severity, string> = {
  low: "#9dbfb7",
  medium: "#e2b866",
  high: "#e3996f",
  critical: "#e07770",
};

export function isSeverity(value: unknown): value is Severity {
  return typeof value === "string" && value in SEVERITY_RANK;
}

export function severityRank(severity: Severity | null | undefined): number {
  return severity ? SEVERITY_RANK[severity] : -1;
}

export function severityColor(severity: Severity | null | undefined): string {
  return severity ? SEVERITY_COLORS[severity] : COLORS.muted;
}

export function severityTextColor(severity: Severity | null | undefined): string {
  return severity ? SEVERITY_TEXT_COLORS[severity] : COLORS.muted;
}

export function isHighOrCritical(severity: Severity | null | undefined): boolean {
  return severity === "high" || severity === "critical";
}

/** Sorts most severe first. */
export function compareSeverity(a: Severity, b: Severity): number {
  return SEVERITY_RANK[b] - SEVERITY_RANK[a];
}

export function maxSeverity(
  severities: ReadonlyArray<Severity | null | undefined>,
): Severity | null {
  let best: Severity | null = null;
  for (const severity of severities) {
    if (severity && severityRank(severity) > severityRank(best)) {
      best = severity;
    }
  }
  return best;
}
