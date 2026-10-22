import { useLayoutEffect, useRef } from "react";
import type { EventOut, Severity } from "../../types";
import type { ServiceFilter, SeverityFilter } from "../../hooks/useFilters";
import { eventKey } from "../../lib/events";
import { TECHNIQUE_IDS, techniqueLabel } from "../../lib/techniques";
import { Panel } from "../layout/Panel";
import { EmptyState } from "../ui/EmptyState";
import { EventRow } from "./EventRow";

const SELECT_CLASS =
  "h-6 border border-console-border bg-console-panel px-1.5 font-mono text-[9.5px] text-console-muted transition-colors hover:border-console-border-strong hover:text-console-text focus-visible:outline-2 focus-visible:outline-console-accent";

interface EventTableProps {
  events: EventOut[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  paused: boolean;
  onTogglePause: () => void;
  pendingCount: number;
  service: ServiceFilter;
  onServiceChange: (value: ServiceFilter) => void;
  severity: SeverityFilter;
  onSeverityChange: (value: SeverityFilter) => void;
  technique: string;
  onTechniqueChange: (value: string) => void;
  activeFilterCount: number;
  onResetFilters: () => void;
  onSelectEvent: (event: EventOut) => void;
}

export function EventTable({
  events,
  loading,
  error,
  onRetry,
  paused,
  onTogglePause,
  pendingCount,
  service,
  onServiceChange,
  severity,
  onSeverityChange,
  technique,
  onTechniqueChange,
  activeFilterCount,
  onResetFilters,
  onSelectEvent,
}: EventTableProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const previousFirst = useRef<string | null>(null);

  useLayoutEffect(() => {
    const element = scrollRef.current;
    const first = events[0] ? eventKey(events[0]) : null;

    if (
      element &&
      first &&
      previousFirst.current &&
      first !== previousFirst.current &&
      element.scrollTop > 6
    ) {
      const index = events.findIndex(
        (event) => eventKey(event) === previousFirst.current,
      );
      if (index > 0) element.scrollTop += Math.min(index, 20) * 44;
    }
    previousFirst.current = first;
  }, [events]);

  const filtersActive = activeFilterCount > 0;
  const emptyState = filtersActive ? (
    <EmptyState
      title="No matching intercepts"
      message="The live buffer has no events matching the current filters."
      action={
        <button
          type="button"
          onClick={onResetFilters}
          className="border border-console-border-strong bg-console-panel px-3 py-1.5 font-mono text-[10px] tracking-[0.06em] text-console-text uppercase transition-colors hover:border-console-muted"
        >
          Reset filters
        </button>
      }
    />
  ) : (
    <EmptyState
      title="No attackers yet"
      message="The honeypots are listening. Generate realistic attack traffic to populate the feed."
      command="docker compose exec backend python -m sim.simulate"
    />
  );

  return (
    <Panel
      index="03.2"
      title="Live intercepts"
      subtitle={`${events.length} shown · newest first · 500 max`}
      loading={loading}
      error={events.length === 0 ? error : null}
      onRetry={onRetry}
      empty={!loading && !error && events.length === 0}
      emptyState={emptyState}
      actions={
        <button
          type="button"
          onClick={onTogglePause}
          aria-pressed={paused}
          className={[
            "inline-flex items-center gap-1.5 border px-1.5 py-1 font-mono text-[9px] tracking-[0.06em] uppercase transition-colors focus-visible:outline-2 focus-visible:outline-console-accent",
            paused
              ? "border-console-accent-dim bg-console-panel text-console-accent"
              : "border-console-border text-console-muted hover:border-console-border-strong hover:text-console-text",
          ].join(" ")}
        >
          {paused ? (
            <svg viewBox="0 0 12 12" className="size-2.5" fill="currentColor" aria-hidden="true">
              <path d="M3 1.8v8.4l6.2-4.2L3 1.8Z" />
            </svg>
          ) : (
            <svg viewBox="0 0 12 12" className="size-2.5" fill="currentColor" aria-hidden="true">
              <rect x="2.5" y="1.8" width="2.4" height="8.4" />
              <rect x="7.1" y="1.8" width="2.4" height="8.4" />
            </svg>
          )}
          {paused ? "Resume" : "Pause"}
          {paused && pendingCount > 0 && (
            <span className="font-mono text-[8.5px] text-console-accent">
              +{pendingCount}
            </span>
          )}
        </button>
      }
      bodyClassName="flex min-h-0 flex-col p-0"
      className="h-[560px] xl:h-full"
    >
      <div className="flex flex-wrap items-center gap-1.5 border-b border-console-border bg-console-panel px-2 py-1.5">
        <select
          aria-label="Filter by service"
          value={service}
          onChange={(changeEvent) =>
            onServiceChange(changeEvent.target.value as ServiceFilter)
          }
          className={SELECT_CLASS}
        >
          <option value="all">All services</option>
          <option value="ssh">SSH</option>
          <option value="http">HTTP</option>
        </select>
        <select
          aria-label="Filter by severity"
          value={severity}
          onChange={(changeEvent) =>
            onSeverityChange(changeEvent.target.value as SeverityFilter)
          }
          className={SELECT_CLASS}
        >
          <option value="all">All severities</option>
          {(["low", "medium", "high", "critical"] as Severity[]).map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <select
          aria-label="Filter by ATT&CK technique"
          value={technique}
          onChange={(changeEvent) => onTechniqueChange(changeEvent.target.value)}
          className={`${SELECT_CLASS} max-w-[148px]`}
        >
          <option value="all">All techniques</option>
          {TECHNIQUE_IDS.map((id) => (
            <option key={id} value={id}>
              {id} · {techniqueLabel(id)}
            </option>
          ))}
        </select>
        {filtersActive && (
          <button
            type="button"
            onClick={onResetFilters}
            className="px-1 font-mono text-[9px] text-console-faint underline decoration-console-border underline-offset-2 hover:text-console-text"
          >
            Reset ({activeFilterCount})
          </button>
        )}
        <span className="ml-auto inline-flex items-center gap-1.5 font-mono text-[8.5px] tracking-[0.12em] text-console-faint uppercase">
          <span
            aria-hidden="true"
            className={`size-1.5 ${paused ? "bg-console-accent" : "bg-console-live"}`}
          />
          {paused ? "Paused" : "Streaming"}
        </span>
      </div>

      <div ref={scrollRef} className="scrollbar-thin relative min-h-0 flex-1 overflow-auto">
        <table className="w-full min-w-[500px] table-fixed border-collapse text-left">
          <thead className="sticky top-0 z-10 bg-console-panel-2">
            <tr className="border-b border-console-border">
              <th className="w-[52px] py-1.5 pr-1 pl-2 font-mono text-[8.5px] font-medium tracking-[0.1em] text-console-faint uppercase">
                Time
              </th>
              <th className="w-[44px] py-1.5 font-mono text-[8.5px] font-medium tracking-[0.1em] text-console-faint uppercase">
                Svc
              </th>
              <th className="w-[104px] py-1.5 font-mono text-[8.5px] font-medium tracking-[0.1em] text-console-faint uppercase">
                Source
              </th>
              <th className="hidden w-[78px] py-1.5 font-mono text-[8.5px] font-medium tracking-[0.1em] text-console-faint uppercase 2xl:table-cell">
                Country
              </th>
              <th className="w-[92px] py-1.5 pr-1 pl-1 font-mono text-[8.5px] font-medium tracking-[0.1em] text-console-faint uppercase">
                Technique
              </th>
              <th className="w-[74px] py-1.5 pr-1 font-mono text-[8.5px] font-medium tracking-[0.1em] text-console-faint uppercase">
                Severity
              </th>
              <th className="py-1.5 pr-2 font-mono text-[8.5px] font-medium tracking-[0.1em] text-console-faint uppercase">
                Summary
              </th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <EventRow
                key={eventKey(event)}
                event={event}
                onSelect={onSelectEvent}
              />
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
