import type { ReactNode } from "react";
import type { Stats, WindowKey } from "../../types";
import { compactNumber, pctChange } from "../../lib/format";
import { Panel } from "./Panel";

interface KpiRowProps {
  stats: Stats | null;
  windowKey: WindowKey;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

interface KpiCardProps {
  label: string;
  value: string;
  context: ReactNode;
  accent: string;
  icon: ReactNode;
  loading: boolean;
}

function KpiCard({ label, value, context, accent, icon, loading }: KpiCardProps) {
  return (
    <Panel
      title={label}
      loading={loading}
      actions={
        <span
          className="grid size-6 place-items-center rounded-md border border-console-border/80 bg-white/[0.025]"
          style={{ color: accent }}
          aria-hidden="true"
        >
          {icon}
        </span>
      }
      className="relative h-full"
      bodyClassName="relative overflow-hidden px-4 pt-2.5 pb-3.5"
    >
      <span
        aria-hidden="true"
        className="pointer-events-none absolute -top-9 -right-7 size-20 rounded-full opacity-20 blur-2xl"
        style={{ backgroundColor: accent }}
      />
      <div className="font-mono text-[26px] leading-none font-semibold tracking-tight text-console-text tabular-nums">
        {value}
      </div>
      <div className="mt-2 text-[11px] leading-snug text-console-muted">{context}</div>
    </Panel>
  );
}

function Icon({ path }: { path: string }) {
  return (
    <svg viewBox="0 0 24 24" className="size-3.5" fill="none" aria-hidden="true">
      <path
        d={path}
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
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
      <Panel
        error={error}
        onRetry={onRetry}
        title="Overview"
        subtitle={`Window ${windowKey}`}
      />
    );
  }

  const totals = stats?.totals;
  const delta = totals ? pctChange(totals.events, totals.events_previous) : null;

  const deltaNode =
    delta === null ? (
      <span>vs previous {windowKey}</span>
    ) : (
      <span className="inline-flex items-center gap-1">
        <span
          className={
            delta > 0
              ? "text-[#fbbf24]"
              : delta < 0
                ? "text-[#4ade80]"
                : "text-console-muted"
          }
        >
          {delta > 0 ? "▲" : delta < 0 ? "▼" : "•"} {Math.abs(delta).toFixed(1)}%
        </span>
        <span>vs previous {windowKey}</span>
      </span>
    );

  const cards: Array<Omit<KpiCardProps, "loading">> = [
    {
      label: "Events",
      value: totals ? compactNumber(totals.events) : "—",
      context: deltaNode,
      accent: "#38bdf8",
      icon: <Icon path="M3 17.5 8.5 11l3.6 4L21 5.5M21 5.5h-5M21 5.5v5" />,
    },
    {
      label: "Rate / min",
      value: totals ? totals.events_per_minute.toFixed(1) : "—",
      context: "events per minute",
      accent: "#06b6d4",
      icon: (
        <Icon path="M12 3.5a8.5 8.5 0 1 0 8.5 8.5M12 7.5V12l3 1.8M16.5 3.5h4v4" />
      ),
    },
    {
      label: "Unique sources",
      value: totals ? compactNumber(totals.unique_sources) : "—",
      context: "distinct attacker IPs",
      accent: "#8b5cf6",
      icon: (
        <Icon path="M12 21s6.5-5.4 6.5-11a6.5 6.5 0 1 0-13 0C5.5 15.6 12 21 12 21Z M12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z" />
      ),
    },
    {
      label: "Unique credentials",
      value: totals ? compactNumber(totals.unique_credentials) : "—",
      context: "username + hash pairs",
      accent: "#f59e0b",
      icon: (
        <Icon path="M14.5 9.5a4 4 0 1 1-1.2-2.8M14.5 9.5 20 4M17 7l2 2M19 5l2 2M10 13.5a4.5 4.5 0 1 0 4.5 4.5c0-.7-.2-1.4-.5-2L19 11" />
      ),
    },
    {
      label: "Payloads",
      value: totals ? compactNumber(totals.payloads) : "—",
      context: "ingress download attempts",
      accent: "#f97316",
      icon: (
        <Icon path="M12 3.5v11m0 0 4-4m-4 4-4-4M4.5 16.5v2a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-2" />
      ),
    },
    {
      label: "High + critical",
      value: totals ? compactNumber(totals.high_or_critical) : "—",
      context: "events needing attention",
      accent: "#ef4444",
      icon: <Icon path="M12 3.5 2.8 19.5h18.4L12 3.5Zm0 5.5v5m0 3v.5" />,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-6">
      {cards.map((card) => (
        <KpiCard key={card.label} {...card} loading={loading} />
      ))}
    </div>
  );
}
