import { describe, expect, it } from "vitest";
import {
  TECHNIQUES,
  TECHNIQUE_IDS,
  isTechniqueId,
  techniqueLabel,
  techniqueShortLabel,
} from "./techniques";

describe("techniques", () => {
  it("maps all seven pipeline techniques", () => {
    expect(TECHNIQUE_IDS).toHaveLength(7);
    expect(TECHNIQUES.T1110).toBe("Brute Force");
    expect(TECHNIQUES["T1110.004"]).toBe("Credential Stuffing");
    expect(TECHNIQUES.T1595).toBe("Active Scanning");
    expect(TECHNIQUES.T1190).toBe("Exploit Public-Facing Application");
    expect(TECHNIQUES.T1105).toBe("Ingress Tool Transfer");
    expect(TECHNIQUES.T1059).toBe("Command and Scripting Interpreter");
    expect(TECHNIQUES.T1078).toBe("Valid Accounts");
  });

  it("returns the label for every known id", () => {
    for (const id of TECHNIQUE_IDS) {
      expect(techniqueLabel(id)).toBe(TECHNIQUES[id]);
    }
  });

  it("falls back to Unknown for missing or unrecognised ids", () => {
    expect(techniqueLabel("T9999")).toBe("Unknown");
    expect(techniqueLabel("")).toBe("Unknown");
    expect(techniqueLabel(null)).toBe("Unknown");
    expect(techniqueLabel(undefined)).toBe("Unknown");
  });

  it("recognises only known ids", () => {
    expect(isTechniqueId("T1110")).toBe(true);
    expect(isTechniqueId("T1110.004")).toBe(true);
    expect(isTechniqueId("T1234")).toBe(false);
  });

  it("provides compact labels for dense tables", () => {
    expect(techniqueShortLabel("T1190")).toBe("Exploit Public App");
    expect(techniqueShortLabel("T1059")).toBe("Command Interpreter");
    expect(techniqueShortLabel("T1110")).toBe("Brute Force");
  });
});
