import type { WindowKey } from "../../types";
import { compactNumber } from "../../lib/format";
import type { LiveStatus } from "../../ws/client";
import { ConnectionBadge } from "../ui/ConnectionBadge";

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
    <header className="sticky top-0 z-30 border-b border-console-border/80 bg-console-bg/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1680px] flex-wrap items-center gap-x-4 gap-y-2.5 px-3 py-2.5 sm:px-5 lg:px-6">
        <div className="flex min-w-0 items-center gap-2.5">
          <div className="grid size-9 shrink-0 place-items-center rounded-lg border border-[#f59e0b]/35 bg-gradient-to-br from-[#f59e0b]/20 to-[#f59e0b]/[0.02] text-lg shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
            <span aria-hidden="true">🍯</span>
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="truncate text-[15px] leading-tight font-semibold tracking-tight text-console-text">
                HoneyBadger
              </h1>
              <span className="hidden h-3.5 w-px bg-console-border sm:block" />
              <span className="hidden text-[9px] font-semibold tracking-[0.22em] text-console-muted uppercase sm:block">
                Threat Ops
              </span>
              {mock && (
                <span className="rounded border border-[#f59e0b]/35 bg-[#f59e0b]/10 px-1.5 py-px text-[9px] font-semibold tracking-[0.1em] text-[#fcd34d] uppercase">
                  Mock
                </span>
              )}
            </div>
            <p className="truncate text-[10px] text-console-muted">
              {mock
                ? "Synthetic telemetry — no backend required"
                : "Live honeypot telemetry"}
            </p>
          </div>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-2 sm:gap-2.5">
          <ConnectionBadge status={connection} attempt={attempt} />

          <div
            className="hidden items-baseline gap-1.5 rounded-lg border border-console-border bg-console-panel-2/80 px-2.5 py-1.5 md:flex"
            title={generatedAt ? `Stats generated at ${generatedAt}` : undefined}
          >
            <span className="text-[9px] font-medium tracking-[0.12em] text-console-muted uppercase">
              Events · {windowKey}
            </span>
            <span className="font-mono text-sm leading-none font-semibold text-console-text tabular-nums">
              {totalEvents === null ? "—" : compactNumber(totalEvents)}
            </span>
          </div>

          <div
            role="group"
            aria-label="Time window"
            className="flex items-center gap-0.5 rounded-lg border border-console-border bg-console-panel-2/80 p-0.5"
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
                    "rounded-md px-2 py-1 font-mono text-[11px] transition-colors focus-visible:outline-2 focus-visible:outline-[#38bdf8]",
                    active
                      ? "bg-[#38bdf8]/15 text-[#7dd3fc] shadow-[inset_0_0_0_1px_rgba(56,189,248,0.3)]"
                      : "text-console-muted hover:bg-white/[0.05] hover:text-console-text",
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
            className="inline-flex items-center gap-1 rounded-lg border border-console-border bg-console-panel-2/80 px-2.5 py-1.5 text-[11px] font-medium text-console-muted transition-colors hover:border-console-muted/40 hover:text-console-text focus-visible:outline-2 focus-visible:outline-[#38bdf8]"
          >
            Grafana
            <svg viewBox="0 0 16 16" className="size-3" fill="none" aria-hidden="true">
              <path
                d="M6 3.5h6.5V10M12.5 3.5 5 11"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M11 9.2v3.3H3.5V5H7"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
                opacity=".55"
              />
            </svg>
          </a>
        </div>
      </div>
    </header>
  );
}
