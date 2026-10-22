import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
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
    <div className="border border-console-border-strong bg-console-panel px-2.5 py-2">
      <div className="mb-1.5 flex items-baseline justify-between gap-4 border-b border-console-border pb-1.5">
        <span className="font-mono text-[9px] tracking-[0.08em] text-console-muted">
          {label}
        </span>
        <span className="font-mono text-[10px] text-console-text tabular-nums">
          {total} evt
        </span>
      </div>
      <div className="space-y-1">
        {series.map((item) => {
          const entry = payload.find((candidate) => candidate.dataKey === item.key);
          const value = typeof entry?.value === "number" ? entry.value : 0;
          return (
            <div key={item.key} className="flex items-center gap-2 text-[10px]">
              <span
                aria-hidden="true"
                className="size-1.5 shrink-0"
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

  const totals = useMemo(
    () =>
      series.map((item) => ({
        ...item,
        total: points.reduce(
          (sum, point) => sum + (point[item.key as keyof ActivityPoint] as number),
          0,
        ),
      })),
    [points, series],
  );

  const peak = useMemo(() => {
    let best: ActivityPoint | null = null;
    for (const point of points) {
      if (!best || point.total > best.total) best = point;
    }
    return best;
  }, [points]);

  const bucketLabel = timeseries
    ? timeseries.bucket_seconds <= 60
      ? "1 min"
      : `${Math.round(timeseries.bucket_seconds / 60)} min`
    : null;

  const empty = !loading && !error && points.every((point) => point.total === 0);

  return (
    <Panel
      index="02.1"
      title="Attack signal"
      subtitle={
        <>
          Volume per {bucketLabel ?? "bucket"} · stacked by {mode}
          {peak && peak.total > 0 ? ` · peak ${peak.total} at ${peak.label}` : ""}
        </>
      }
      loading={false}
      error={error}
      onRetry={onRetry}
      empty={empty}
      emptyState={
        <div className="flex h-[292px] flex-col items-center justify-center gap-2 text-center">
          <span className="font-mono text-[10px] tracking-[0.16em] text-console-faint uppercase">
            Quiet window
          </span>
          <span className="max-w-xs text-[11px] text-console-muted">
            No attacker activity in the last {windowKey}. Widen the window or run the
            simulator.
          </span>
        </div>
      }
      actions={
        <div
          role="group"
          aria-label="Chart grouping"
          className="flex items-center border border-console-border"
        >
          {(["service", "severity"] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setMode(option)}
              aria-pressed={mode === option}
              className={[
                "border-r border-console-border px-2 py-1 font-mono text-[9px] tracking-[0.08em] uppercase transition-colors last:border-r-0",
                mode === option
                  ? "bg-console-panel text-console-accent"
                  : "text-console-faint hover:text-console-text",
              ].join(" ")}
            >
              {option}
            </button>
          ))}
        </div>
      }
      bodyClassName="flex flex-col px-2 pt-4 pb-2 sm:px-3"
      className="h-full"
    >
      {loading ? (
        <ChartSkeleton />
      ) : (
        <>
          <div className="min-h-[286px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={points}
                margin={{ top: 4, right: 6, left: -22, bottom: 0 }}
                barCategoryGap="18%"
              >
                <CartesianGrid
                  stroke={COLORS.grid}
                  strokeOpacity={0.7}
                  strokeDasharray="2 4"
                  vertical={false}
                />
                <XAxis
                  dataKey="label"
                  tick={{ fill: COLORS.faint, fontSize: 9 }}
                  tickLine={false}
                  axisLine={{ stroke: COLORS.border }}
                  minTickGap={28}
                  dy={4}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: COLORS.faint, fontSize: 9 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value: number) => compactNumber(value)}
                  width={46}
                />
                <Tooltip
                  cursor={{ fill: "rgba(226,233,232,0.04)" }}
                  content={<ActivityTooltip series={series} />}
                />
                {series.map((item) => (
                  <Bar
                    key={item.key}
                    dataKey={item.key}
                    name={item.label}
                    stackId="signal"
                    fill={item.color}
                    fillOpacity={0.82}
                    stroke="none"
                    isAnimationActive={false}
                    maxBarSize={22}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-1 flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5 border-t border-console-border/70 px-1 pt-2">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
              {totals.map((item) => (
                <span
                  key={item.key}
                  className="inline-flex items-baseline gap-1.5 font-mono text-[9px] text-console-muted"
                >
                  <span
                    aria-hidden="true"
                    className="size-1.5 self-center"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="tracking-[0.06em] uppercase">{item.label}</span>
                  <span className="text-console-text tabular-nums">
                    {compactNumber(item.total)}
                  </span>
                </span>
              ))}
            </div>
            <span className="font-mono text-[8.5px] tracking-[0.1em] text-console-faint uppercase">
              {points.length} buckets · {windowKey}
            </span>
          </div>
        </>
      )}
    </Panel>
  );
}
