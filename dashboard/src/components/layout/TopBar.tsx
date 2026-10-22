import type { WindowKey } from "../../types";
import { compactNumber } from "../../lib/format";
import type { LiveStatus } from "../../ws/client";
import { ConnectionBadge } from "../ui/ConnectionBadge";
import { UtcClock } from "./UtcClock";

const WINDOWS: readonly WindowKey[] = ["15m", "1h", "6h", "24h", "7d"];

interface TopBarProps {
  windowKey: WindowKey;
  onWindowChange: (window: WindowKey) => void;
  connection: LiveStatus;
  attempt: number;
  totalEvents: number | null;
  generatedAt?: string | null;
  mock: boolean;
}

export function TopBar({
  windowKey,
  onWindowChange,
  connection,
  attempt,
  totalEvents,
  generatedAt,
  mock,
}: TopBarProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-console-border bg-console-bg">
      <div className="mx-auto flex max-w-[1720px] flex-wrap items-center gap-x-4 gap-y-2.5 px-4 py-2.5 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <a
            href="#overview"
            aria-label="HoneyBadger overview"
            className="grid size-9 shrink-0 place-items-center border border-console-border bg-console-panel lg:hidden"
          >
            <svg viewBox="0 0 32 32" className="size-5" aria-hidden="true">
              <path
                d="M16 2.8 27.4 9.4v13.2L16 29.2 4.6 22.6V9.4Z"
                fill="none"
                stroke="#72e3a4"
                strokeWidth="1.3"
              />
              <path d="M16 9.6 21.8 13v6.2L16 22.4l-5.8-3.2V13Z" fill="#72e3a4" />
              <path d="M16 13.7 18.7 15.2v3.1L16 19.8l-2.7-1.5v-3.1Z" fill="#080b0d" />
            </svg>
          </a>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[9px] leading-none font-medium tracking-[0.2em] text-console-accent uppercase">
                HoneyBadger · HB-01
              </span>
              <span aria-hidden="true" className="hidden h-2.5 w-px bg-console-border-strong sm:block" />
              <span className="hidden font-mono text-[9px] tracking-[0.16em] text-console-faint uppercase sm:block">
                Honeypot telemetry
              </span>
              {mock && (
                <span className="border border-console-accent-dim px-1 py-px font-mono text-[8.5px] leading-none tracking-[0.14em] text-console-accent uppercase">
                  Mock data
                </span>
              )}
            </div>
            <h1 className="mt-1 font-display text-[24px] leading-none font-semibold tracking-[-0.01em] text-console-text">
              Threat Operations
            </h1>
            <p className="mt-1 hidden text-[10px] leading-none text-console-muted md:block">
              SSH :8022 · HTTP :8081 · ingestion + ATT&amp;CK enrichment
            </p>
          </div>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-x-4 gap-y-2">
          <UtcClock />
          <ConnectionBadge status={connection} attempt={attempt} />

          <div
            className="hidden border-l border-console-border pl-4 sm:block"
            title={generatedAt ? `Stats generated at ${generatedAt}` : undefined}
          >
            <div className="label text-console-faint">Events / {windowKey}</div>
            <div className="mt-1 font-display text-[18px] leading-none font-semibold text-console-text tabular-nums">
              {totalEvents === null ? "—" : compactNumber(totalEvents)}
            </div>
          </div>

          <div
            role="group"
            aria-label="Time window"
            className="flex items-center border border-console-border"
          >
            {WINDOWS.map((window) => {
              const active = window === windowKey;
              return (
                <button
                  key={window}
                  type="button"
                  onClick={() => onWindowChange(window)}
                  aria-pressed={active}
                  className={[
                    "min-w-8 border-r border-console-border px-1.5 py-1 font-mono text-[10px] leading-none transition-colors last:border-r-0",
                    active
                      ? "bg-console-panel-2 text-console-accent"
                      : "text-console-muted hover:bg-console-panel hover:text-console-text",
                  ].join(" ")}
                >
                  {window}
                </button>
              );
            })}
          </div>

          <a
            href="http://localhost:3001"
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex items-center gap-1.5 border border-console-border bg-console-panel px-2 py-1.5 font-mono text-[9px] leading-none tracking-[0.1em] text-console-muted uppercase transition-colors hover:border-console-border-strong hover:text-console-text"
          >
            Grafana
            <svg viewBox="0 0 16 16" className="size-3" fill="none" aria-hidden="true">
              <path
                d="M6 3.5h6.5V10M12.5 3.5 5 11"
                stroke="currentColor"
                strokeWidth="1.3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </a>
        </div>
      </div>
    </header>
  );
}
