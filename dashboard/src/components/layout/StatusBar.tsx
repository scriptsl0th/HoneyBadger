import type { LiveStatus } from "../../ws/client";
import type { WindowKey } from "../../types";
import { compactNumber } from "../../lib/format";
import { UtcClock } from "./UtcClock";

const LABEL: Record<LiveStatus, string> = {
  live: "live",
  polling: "polling",
  connecting: "connecting",
  reconnecting: "reconnecting",
};

const DOT: Record<LiveStatus, string> = {
  live: "bg-[#63d69b]",
  polling: "bg-[#5fa8c7]",
  connecting: "bg-[#cfa84f]",
  reconnecting: "bg-[#cfa84f]",
};

interface StatusBarProps {
  status: LiveStatus;
  windowKey: WindowKey;
  totalEvents: number | null;
  generatedAt: string | null;
  activeFilterCount: number;
}

/** TUI-style status line: session state, filters, totals, clock. */
export function StatusBar({
  status,
  windowKey,
  totalEvents,
  generatedAt,
  activeFilterCount,
}: StatusBarProps) {
  return (
    <footer
      aria-label="Console status"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-console-border bg-console-bg lg:left-[52px]"
    >
      <div className="mx-auto flex h-7 max-w-[1720px] items-center gap-2 overflow-hidden px-3 font-mono text-[8.5px] tracking-[0.08em] whitespace-nowrap text-console-faint uppercase sm:gap-3 sm:px-6">
        <span className="inline-flex items-center gap-1.5 text-console-muted">
          <span aria-hidden="true" className={`size-1.5 ${DOT[status]}`} />
          {LABEL[status]}
        </span>

        <span aria-hidden="true" className="text-console-border-strong">
          |
        </span>
        <span className="hidden sm:inline">hb-01</span>
        <span className="hidden md:inline" title="Read-only console · payloads are never fetched">
          read-only · hashes only
        </span>

        <button
          type="button"
          aria-label="Focus console command line"
          onClick={() => {
            const input = document.querySelector<HTMLInputElement>(
              'input[name="console-command"]',
            );
            if (!input) return;
            input.scrollIntoView({ block: "center" });
            input.focus({ preventScroll: true });
          }}
          className="ml-auto inline-flex shrink-0 items-center gap-1 font-mono text-[8.5px] tracking-[0.08em] text-console-faint uppercase transition-colors hover:text-console-text focus-visible:outline-2 focus-visible:outline-console-accent"
        >
          <span aria-hidden="true" className="text-console-accent">
            /
          </span>
          cmd
          <span className="hidden lg:inline">· ↑↓ history</span>
        </button>

        <span className="flex items-center gap-2 sm:gap-3">
          {activeFilterCount > 0 && (
            <span className="text-console-accent">filters {activeFilterCount}</span>
          )}
          <span className="hidden sm:inline">
            {totalEvents === null ? "evt —" : `evt ${compactNumber(totalEvents)}`}
          </span>
          <span>win {windowKey}</span>
          <span title={generatedAt ? `Stats generated ${generatedAt}` : "Awaiting telemetry"}>
            <UtcClock compact />
          </span>
        </span>
      </div>
    </footer>
  );
}
