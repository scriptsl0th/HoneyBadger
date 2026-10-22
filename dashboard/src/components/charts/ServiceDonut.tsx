import { useMemo } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { ServiceCount } from "../../types";
import { serviceColor, serviceLabel } from "../../lib/colors";
import { compactNumber } from "../../lib/format";
import { Panel } from "../layout/Panel";

interface ServiceDonutProps {
  services: ServiceCount[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

interface Datum {
  service: "ssh" | "http";
  name: string;
  value: number;
  color: string;
}

interface TooltipEntry {
  payload?: Datum;
}

interface DonutTooltipProps {
  active?: boolean;
  payload?: TooltipEntry[];
}

function DonutTooltip({ active, payload }: DonutTooltipProps) {
  const datum = payload?.[0]?.payload;
  if (!active || !datum) return null;
  return (
    <div className="rounded-lg border border-console-border bg-[#0b1322]/95 px-3 py-2 shadow-xl">
      <div className="flex items-center gap-2 text-xs">
        <span
          className="size-2 rounded-full"
          style={{ backgroundColor: datum.color }}
        />
        <span className="text-console-muted">{datum.name}</span>
        <span className="ml-auto font-mono text-console-text">{datum.value}</span>
      </div>
    </div>
  );
}

export function ServiceDonut({
  services,
  loading,
  error,
  onRetry,
}: ServiceDonutProps) {
  const data: Datum[] = useMemo(
    () =>
      (services ?? [])
        .filter((item) => item.count > 0)
        .map((item) => ({
          service: item.service,
          name: serviceLabel(item.service),
          value: item.count,
          color: serviceColor(item.service),
        })),
    [services],
  );

  const total = (services ?? []).reduce((sum, item) => sum + item.count, 0);
  const empty = !loading && !error && total === 0;

  return (
    <Panel
      title="Service mix"
      subtitle="SSH vs HTTP share of events"
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={empty}
      emptyState={
        <div className="flex h-[164px] flex-col items-center justify-center gap-1.5 text-center">
          <span className="text-sm font-medium text-console-text">No service data</span>
          <span className="text-xs text-console-muted">
            Waiting for SSH or HTTP honeypot traffic.
          </span>
        </div>
      }
      bodyClassName="px-3 pt-1 pb-3"
    >
      {loading ? (
        <div
          className="mx-auto my-3 size-[152px] animate-pulse rounded-full border-[18px] border-white/[0.045] motion-reduce:animate-none"
          aria-hidden="true"
        />
      ) : (
        <>
          <div className="relative h-[164px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={51}
                  outerRadius={72}
                  paddingAngle={3}
                  stroke="none"
                  isAnimationActive={false}
                >
                  {data.map((item) => (
                    <Cell key={item.service} fill={item.color} fillOpacity={0.9} />
                  ))}
                </Pie>
                <Tooltip content={<DonutTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-mono text-xl leading-none font-semibold text-console-text tabular-nums">
                {compactNumber(total)}
              </span>
              <span className="mt-1 text-[9px] tracking-[0.16em] text-console-muted uppercase">
                events
              </span>
            </div>
          </div>
          <div className="mt-1 grid grid-cols-2 gap-2">
            {(services ?? []).map((item) => {
              const percent = total > 0 ? Math.round((item.count / total) * 100) : 0;
              return (
                <div
                  key={item.service}
                  className="flex items-center gap-1.5 rounded border border-console-border/70 bg-white/[0.02] px-2 py-1"
                >
                  <span
                    className="size-1.5 rounded-full"
                    style={{ backgroundColor: serviceColor(item.service) }}
                  />
                  <span className="text-[10px] text-console-muted uppercase">
                    {serviceLabel(item.service)}
                  </span>
                  <span className="ml-auto font-mono text-[10px] text-console-text tabular-nums">
                    {percent}%
                  </span>
                </div>
              );
            })}
          </div>
        </>
      )}
    </Panel>
  );
}
