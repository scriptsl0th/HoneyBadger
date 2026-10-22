import { describe, expect, it } from "vitest";
import { COLORS } from "./colors";
import {
  SEVERITY_COLORS,
  SEVERITY_ORDER,
  SEVERITY_RANK,
  compareSeverity,
  isHighOrCritical,
  maxSeverity,
  severityColor,
  severityRank,
} from "./severity";

describe("severity", () => {
  it("orders severities low to critical", () => {
    expect(SEVERITY_ORDER).toEqual(["low", "medium", "high", "critical"]);
    expect(severityRank("low")).toBeLessThan(severityRank("medium"));
    expect(severityRank("medium")).toBeLessThan(severityRank("high"));
    expect(severityRank("high")).toBeLessThan(severityRank("critical"));
    expect(SEVERITY_RANK.critical).toBe(3);
  });

  it("uses the console colour tokens", () => {
    expect(SEVERITY_COLORS.low).toBe("#38bdf8");
    expect(SEVERITY_COLORS.medium).toBe("#f59e0b");
    expect(SEVERITY_COLORS.high).toBe("#f97316");
    expect(SEVERITY_COLORS.critical).toBe("#ef4444");
    expect(severityColor(null)).toBe(COLORS.muted);
  });

  it("only flags high and critical as actionable", () => {
    expect(isHighOrCritical("low")).toBe(false);
    expect(isHighOrCritical("medium")).toBe(false);
    expect(isHighOrCritical("high")).toBe(true);
    expect(isHighOrCritical("critical")).toBe(true);
    expect(isHighOrCritical(null)).toBe(false);
  });

  it("compares and picks the maximum severity", () => {
    const sorted = (["low", "critical", "medium", "high"] as const)
      .slice()
      .sort(compareSeverity);
    expect(sorted).toEqual(["critical", "high", "medium", "low"]);

    expect(maxSeverity(["low", null, "critical", "medium"])).toBe("critical");
    expect(maxSeverity([])).toBeNull();
  });
});
