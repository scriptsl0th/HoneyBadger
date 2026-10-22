import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Timeseries, WindowKey } from "../../types";
import { COLORS, SEVERITY_SERIES, SERVICE_SERIES } from "../../lib/colors";
import { compactNumber, formatBucketLabel } from "../../lib/format";
import { Panel } from "../layout/Panel";
import { Skeleton } from "../ui/Skeleton";

type Mode = "service" | "severity";

interface ActivityChartProps {
  timeseries: Timeseries | null;
  windowKey: WindowKey;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

interface ActivityPoint {
  label: string;
  total: number;
  ssh: number;
  http: number;
  low: number;
  medium: number;
  high: number;
  critical: number;
}

interface Series {
  key: string;
  label: string;
  color: string;
}

interface TooltipEntry {
  dataKey?: string | number;
  value?: number | string;
  payload?: ActivityPoint;
}

interface ActivityTooltipProps {
  active?: boolean;
  payload?: TooltipEntry[];
  label?: string | number;
  series: Series[];
}

function ActivityTooltip({ active, payload, label, series }: ActivityTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const total = payload[0]?.payload?.total ?? 0;
  return (
    <div className="rounded-lg border border-console-border bg-[#0b1322]/95 px-3 py-2 shadow-xl backdrop-blur">
      <div className="mb-1.5 flex items-center justify-between gap-4">
        <span className="font-mono text-[10px] text-console-muted">{label}</span>
        <span className="font-mono text-[10px] text-console-text">
          {total} evt
        </span>
      </div>
      <div className="space-y-1">
        {series.map((item) => {
          const entry = payload.find((candidate) => candidate.dataKey === item.key);
          const value = typeof entry?.value === "number" ? entry.value : 0;
          return (
            <div key={item.key} className="flex items-center gap-2 text-[11px]">
              <span
                className="size-1.5 rounded-full"
                style={{ backgroundColor: item.color }}
              />
              <span className="flex-1 text-console-muted">{item.label}</span>
              <span className="font-mono text-console-text tabular-nums">{value}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="space-y-3" aria-hidden="true">
      <Skeleton className="h-[248px] w-full" />
      <div className="flex justify-center gap-4">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-2.5 w-14" />
        ))}
      </div>
    </div>
  );
}

export function ActivityChart({
  timeseries,
  windowKey,
  loading,
  error,
  onRetry,
}: ActivityChartProps) {
  const [mode, setMode] = useState<Mode>("service");

  const series: Series[] = useMemo(
    () =>
      (mode === "service" ? SERVICE_SERIES : SEVERITY_SERIES).map((item) => ({
        key: item.key,
        label: item.label,
        color: item.color,
      })),
    [mode],
  );

  const points: ActivityPoint[] = useMemo(
    () =>
      (timeseries?.points ?? []).map((point) => ({
        ...point,
        label: formatBucketLabel(point.ts, windowKey),
      })),
    [timeseries, windowKey],
  );

  const empty = !loading && !error && points.every((point) => point.total === 0);

  return (
    <Panel
      title="Attack activity"
      subtitle={
        timeseries
          ? `Stacked by ${mode} · ${timeseries.bucket_seconds <= 60 ? "1 min" : `${Math.round(timeseries.bucket_seconds / 60)} min`} buckets`
          : "Stacked volume over time"
      }
      loading={false}
      error={error}
      onRetry={onRetry}
      empty={empty}
      emptyState={
        <div className="flex h-[292px] flex-col items-center justify-center gap-2 text-center">
          <span className="text-sm font-medium text-console-text">Quiet window</span>
          <span className="max-w-xs text-xs text-console-muted">
            No attacker activity in the last {windowKey}. Try a wider window.
          </span>
        </div>
      }
      actions={
        <div
          role="group"
          aria-label="Chart grouping"
          className="flex items-center gap-0.5 rounded-md border border-console-border bg-console-bg/50 p-0.5"
        >
          {(["service", "severity"] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setMode(option)}
              aria-pressed={mode === option}
              className={[
                "rounded px-2 py-0.5 text-[10px] font-medium capitalize transition-colors focus-visible:outline-2 focus-visible:outline-[#38bdf8]",
                mode === option
                  ? "bg-white/[0.08] text-console-text"
                  : "text-console-muted hover:text-console-text",
              ].join(" ")}
            >
              {option}
            </button>
          ))}
        </div>
      }
      bodyClassName="flex flex-col px-2 pt-4 pb-3 sm:px-3"
      className="h-full"
    >
      {loading ? (
        <ChartSkeleton />
      ) : (
        <>
          <div className="min-h-[286px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={points} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                {series.map((item) => (
                  <linearGradient
                    key={item.key}
                    id={`activity-${item.key}`}
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="0%" stopColor={item.color} stopOpacity={0.42} />
                    <stop offset="100%" stopColor={item.color} stopOpacity={0.03} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid
                stroke={COLORS.grid}
                strokeOpacity={0.55}
                strokeDasharray="3 4"
                vertical={false}
              />
              <XAxis
                dataKey="label"
                tick={{ fill: COLORS.muted, fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: COLORS.grid }}
                minTickGap={26}
                dy={4}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: COLORS.muted, fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value: number) => compactNumber(value)}
                width={48}
              />
              <Tooltip
                cursor={{ stroke: COLORS.muted, strokeOpacity: 0.35, strokeDasharray: "3 3" }}
                content={<ActivityTooltip series={series} />}
              />
              {series.map((item, index) => (
                <Area
                  key={item.key}
                  type="monotone"
                  dataKey={item.key}
                  name={item.label}
                  stackId="activity"
                  stroke={item.color}
                  strokeWidth={1.5}
                  fill={`url(#activity-${item.key})`}
                  fillOpacity={1}
                  isAnimationActive={false}
                  activeDot={{ r: 2.5, strokeWidth: 0 }}
                  dot={false}
                  zIndex={series.length - index}
                />
              ))}
            </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-1 flex flex-wrap items-center justify-center gap-x-4 gap-y-1.5">
            {series.map((item) => (
              <span
                key={item.key}
                className="inline-flex items-center gap-1.5 text-[10px] text-console-muted"
              >
                <span
                  className="size-1.5 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                {item.label}
              </span>
            ))}
          </div>
        </>
      )}
    </Panel>
  );
}
