/** MITRE ATT&CK techniques emitted by the HoneyBadger enrichment pipeline. */
export const TECHNIQUES = {
  T1110: "Brute Force",
  "T1110.004": "Credential Stuffing",
  T1595: "Active Scanning",
  T1190: "Exploit Public-Facing Application",
  T1105: "Ingress Tool Transfer",
  T1059: "Command and Scripting Interpreter",
  T1078: "Valid Accounts",
} as const;

export type TechniqueId = keyof typeof TECHNIQUES;

export const TECHNIQUE_IDS = Object.keys(TECHNIQUES) as TechniqueId[];

export function isTechniqueId(value: unknown): value is TechniqueId {
  return typeof value === "string" && value in TECHNIQUES;
}

/** Returns a human label for a technique id; unknown or missing ids are "Unknown". */
export function techniqueLabel(id: string | null | undefined): string {
  if (!id) return "Unknown";
  return isTechniqueId(id) ? TECHNIQUES[id] : "Unknown";
}

/** Compact label for dense tables; full names remain available via techniqueLabel(). */
export function techniqueShortLabel(id: string | null | undefined): string {
  const label = techniqueLabel(id);
  if (label === "Exploit Public-Facing Application") return "Exploit Public App";
  if (label === "Command and Scripting Interpreter") return "Command Interpreter";
  return label;
}
