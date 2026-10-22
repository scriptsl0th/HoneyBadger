import type { ReactNode } from "react";
import type { Stats, WindowKey } from "../../types";
import { compactNumber, pctChange } from "../../lib/format";
import { ErrorState } from "../ui/ErrorState";

interface KpiRowProps {
  stats: Stats | null;
  windowKey: WindowKey;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

interface KpiCellProps {
  index: string;
  label: string;
  value: string;
  unit?: string;
  context: ReactNode;
  valueClassName?: string;
  marker?: "critical" | null;
  loading: boolean;
}

function KpiCell({
  index,
  label,
  value,
  unit,
  context,
  valueClassName = "text-console-text",
  marker = null,
  loading,
}: KpiCellProps) {
  return (
    <div className="relative bg-console-panel px-3 py-2.5">
      <div className="flex items-baseline gap-1.5">
        <span className="font-mono text-[8.5px] leading-none text-console-faint" aria-hidden="true">
          {index}
        </span>
        <span className="label truncate text-console-muted">{label}</span>
      </div>
      <div className="mt-2 flex items-baseline gap-1.5">
        <span
          className={`font-display text-[29px] leading-none font-semibold tabular-nums ${valueClassName}`}
          aria-busy={loading || undefined}
        >
          {value}
        </span>
        {unit && (
          <span className="font-mono text-[9px] leading-none text-console-faint">
            {unit}
          </span>
        )}
      </div>
      <div className="mt-1.5 truncate text-[10px] leading-tight text-console-muted">
        {context}
      </div>
      {marker === "critical" && (
        <span
          aria-hidden="true"
          className="absolute inset-x-0 bottom-0 h-[2px] bg-console-critical"
        />
      )}
    </div>
  );
}

export function KpiRow({
  stats,
  windowKey,
  loading,
  error,
  onRetry,
}: KpiRowProps) {
  if (error && !stats) {
    return (
      <div className="border border-console-border bg-console-panel">
        <ErrorState message={error} onRetry={onRetry} title="Overview unavailable" />
      </div>
    );
  }

  const totals = stats?.totals;
  const delta = totals ? pctChange(totals.events, totals.events_previous) : null;

  const deltaNode =
    delta === null ? (
      <span>no prior {windowKey} baseline</span>
    ) : (
      <span className="inline-flex items-baseline gap-1">
        <span
          className={
            delta > 0
              ? "text-console-accent"
              : delta < 0
                ? "text-console-live"
                : "text-console-muted"
          }
        >
          {delta > 0 ? "▲" : delta < 0 ? "▼" : "•"} {Math.abs(delta).toFixed(1)}%
        </span>
        <span>vs prev {windowKey}</span>
      </span>
    );

  const cards: Array<Omit<KpiCellProps, "loading">> = [
    {
      index: "01",
      label: "Events",
      value: totals ? compactNumber(totals.events) : "—",
      context: deltaNode,
    },
    {
      index: "02",
      label: "Rate",
      value: totals ? totals.events_per_minute.toFixed(1) : "—",
      unit: "evt/min",
      context: "current throughput",
    },
    {
      index: "03",
      label: "Sources",
      value: totals ? compactNumber(totals.unique_sources) : "—",
      context: "distinct attacker IPs",
    },
    {
      index: "04",
      label: "Credentials",
      value: totals ? compactNumber(totals.unique_credentials) : "—",
      context: "username + hash pairs",
    },
    {
      index: "05",
      label: "Payloads",
      value: totals ? compactNumber(totals.payloads) : "—",
      context: "ingress transfer attempts",
    },
    {
      index: "06",
      label: "High + critical",
      value: totals ? compactNumber(totals.high_or_critical) : "—",
      context: totals?.high_or_critical ? "queued for triage" : "no elevated events",
      valueClassName:
        totals && totals.high_or_critical > 0
          ? "text-sev-critical"
          : "text-console-text",
      marker: totals && totals.high_or_critical > 0 ? "critical" : null,
    },
  ];

  return (
    <section
      id="overview"
      aria-label="Overview readouts"
      className="scroll-mt-24 border border-console-border bg-console-border"
    >
      <div className="grid grid-cols-2 gap-px md:grid-cols-3 xl:grid-cols-6">
        {cards.map((card) => (
          <KpiCell key={card.label} {...card} loading={loading} />
        ))}
      </div>
    </section>
  );
}
