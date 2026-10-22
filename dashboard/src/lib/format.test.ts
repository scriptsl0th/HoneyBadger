import { describe, expect, it } from "vitest";
import type { EventOut } from "../types";
import {
  compactNumber,
  eventSummary,
  formatBytes,
  pctChange,
  relativeTime,
  shortHash,
  truncate,
} from "./format";

const HASH = `sha256:${"0123456789abcdef".repeat(4)}`;

function makeEvent(overrides: Partial<EventOut> = {}): EventOut {
  return {
    service: "ssh",
    source_ip: "203.0.113.10",
    timestamp: "2026-01-01T11:59:50.000Z",
    login_info: { username: "root", password_hash: HASH },
    user_agent: null,
    http_method: null,
    http_path: null,
    http_status_code: null,
    command: null,
    payload_url: null,
    payload_hash: null,
    payload_size: null,
    geo_info: null,
    technique_id: "T1110",
    severity: "medium",
    ...overrides,
  };
}

describe("relativeTime", () => {
  const now = Date.parse("2026-01-01T12:00:00.000Z");

  it("formats seconds, minutes, hours and days", () => {
    expect(relativeTime("2026-01-01T11:59:50.000Z", now)).toBe("10s ago");
    expect(relativeTime("2026-01-01T11:55:00.000Z", now)).toBe("5m ago");
    expect(relativeTime("2026-01-01T09:00:00.000Z", now)).toBe("3h ago");
    expect(relativeTime("2025-12-30T12:00:00.000Z", now)).toBe("2d ago");
  });

  it("treats very recent and future timestamps as just now", () => {
    expect(relativeTime("2026-01-01T11:59:58.000Z", now)).toBe("just now");
    expect(relativeTime("2026-01-01T12:01:00.000Z", now)).toBe("just now");
  });

  it("returns a dash for missing or invalid input", () => {
    expect(relativeTime(null, now)).toBe("—");
    expect(relativeTime("not-a-date", now)).toBe("—");
  });
});

describe("compactNumber", () => {
  it("keeps small integers intact", () => {
    expect(compactNumber(0)).toBe("0");
    expect(compactNumber(999)).toBe("999");
  });

  it("compacts thousands, millions and billions", () => {
    expect(compactNumber(1000)).toBe("1k");
    expect(compactNumber(1500)).toBe("1.5k");
    expect(compactNumber(12_400)).toBe("12.4k");
    expect(compactNumber(1_234_567)).toBe("1.2M");
    expect(compactNumber(2_500_000_000)).toBe("2.5B");
  });

  it("handles negatives and non-finite values", () => {
    expect(compactNumber(-1500)).toBe("-1.5k");
    expect(compactNumber(Number.NaN)).toBe("—");
  });
});

describe("formatBytes", () => {
  it("formats byte sizes", () => {
    expect(formatBytes(null)).toBe("—");
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5 MB");
  });
});

describe("shortHash", () => {
  it("keeps the prefix and shortens the middle", () => {
    expect(shortHash(HASH)).toBe("sha256:012…cdef");
  });

  it("leaves short or missing values alone", () => {
    expect(shortHash("sha256:abcd")).toBe("sha256:abcd");
    expect(shortHash(null)).toBe("—");
  });
});

describe("pctChange", () => {
  it("computes a rounded percentage change", () => {
    expect(pctChange(150, 100)).toBe(50);
    expect(pctChange(75, 100)).toBe(-25);
    expect(pctChange(100, 100)).toBe(0);
  });

  it("returns null without a baseline", () => {
    expect(pctChange(10, 0)).toBeNull();
  });
});

describe("eventSummary", () => {
  it("describes SSH brute force with the attempted username", () => {
    expect(eventSummary(makeEvent())).toBe("SSH login attempt as root");
    expect(eventSummary(makeEvent({ technique_id: "T1110.004" }))).toBe(
      "SSH credential stuffing as root",
    );
  });

  it("describes HTTP scanning and exploitation", () => {
    expect(
      eventSummary(
        makeEvent({
          service: "http",
          technique_id: "T1595",
          http_method: "GET",
          http_path: "/admin",
          login_info: null,
        }),
      ),
    ).toBe("Scanned GET /admin");

    expect(
      eventSummary(
        makeEvent({
          service: "http",
          technique_id: "T1190",
          http_path: "/wp-login.php",
          login_info: null,
        }),
      ),
    ).toBe("Exploit attempt: /wp-login.php");
  });

  it("describes transfers and command execution", () => {
    expect(
      eventSummary(
        makeEvent({
          technique_id: "T1105",
          payload_url: "http://198.51.100.4/x.sh",
        }),
      ),
    ).toBe("Ingress transfer: http://198.51.100.4/x.sh");

    expect(
      eventSummary(makeEvent({ technique_id: "T1059", command: "id" })),
    ).toBe("Executed: id");
  });

  it("describes valid-account use and falls back for unknown techniques", () => {
    expect(eventSummary(makeEvent({ technique_id: "T1078" }))).toBe(
      "Valid account use: root",
    );

    expect(
      eventSummary(
        makeEvent({
          service: "http",
          technique_id: "T9999",
          http_method: null,
          http_path: "/probe",
        }),
      ),
    ).toBe("HTTP /probe");
  });
});

describe("truncate", () => {
  it("adds an ellipsis only when needed", () => {
    expect(truncate("short", 10)).toBe("short");
    expect(truncate("abcdefghijkl", 8)).toBe("abcdefg…");
  });
});
