import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TechniqueCount } from "../../types";
import { COLORS } from "../../lib/colors";
import { techniqueLabel, techniqueShortLabel } from "../../lib/techniques";
import { Panel } from "../layout/Panel";
import { Badge } from "../ui/Badge";
import { Skeleton } from "../ui/Skeleton";

const TECHNIQUE_COLORS = [
  "#38bdf8",
  "#8b5cf6",
  "#f59e0b",
  "#f97316",
  "#ef4444",
  "#06b6d4",
  "#22c55e",
];

interface TechniqueBarsProps {
  techniques: TechniqueCount[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  selectedTechnique: string;
  onSelectTechnique: (technique: string) => void;
}

interface Datum {
  id: string;
  short: string;
  name: string;
  count: number;
  color: string;
}

interface TooltipEntry {
  payload?: Datum;
}

interface TechniqueTooltipProps {
  active?: boolean;
  payload?: TooltipEntry[];
}

function TechniqueTooltip({ active, payload }: TechniqueTooltipProps) {
  const datum = payload?.[0]?.payload;
  if (!active || !datum) return null;
  return (
    <div className="rounded-lg border border-console-border bg-[#0b1322]/95 px-3 py-2 shadow-xl">
      <div className="font-mono text-[10px] text-console-muted">{datum.id}</div>
      <div className="text-xs font-medium text-console-text">{datum.name}</div>
      <div className="mt-0.5 text-[10px] text-console-muted">
        <span className="font-mono text-console-text">{datum.count}</span> events · click
        to filter
      </div>
    </div>
  );
}

export function TechniqueBars({
  techniques,
  loading,
  error,
  onRetry,
  selectedTechnique,
  onSelectTechnique,
}: TechniqueBarsProps) {
  const data: Datum[] = useMemo(
    () =>
      [...(techniques ?? [])]
        .sort((a, b) => b.count - a.count)
        .slice(0, 7)
        .map((item, index) => ({
          id: item.technique_id,
          short: techniqueShortLabel(item.technique_id),
          name: techniqueLabel(item.technique_id),
          count: item.count,
          color: TECHNIQUE_COLORS[index % TECHNIQUE_COLORS.length],
        })),
    [techniques],
  );

  const total = data.reduce((sum, item) => sum + item.count, 0);
  const empty = !loading && !error && total === 0;

  return (
    <Panel
      title="ATT&CK techniques"
      subtitle={selectedTechnique === "all" ? "Top 7 · click to filter feed" : "Filtering feed by technique"}
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={empty}
      emptyState={
        <div className="flex h-[196px] flex-col items-center justify-center gap-1.5 text-center">
          <span className="text-sm font-medium text-console-text">No techniques yet</span>
          <span className="max-w-[240px] text-xs text-console-muted">
            Classified events will appear here once attacks arrive.
          </span>
        </div>
      }
      actions={
        selectedTechnique !== "all" ? (
          <button
            type="button"
            onClick={() => onSelectTechnique("all")}
            className="rounded border border-console-border bg-white/[0.03] px-2 py-0.5 text-[10px] text-console-muted transition-colors hover:text-console-text focus-visible:outline-2 focus-visible:outline-[#38bdf8]"
          >
            Clear filter
          </button>
        ) : (
          <Badge tone="neutral">Top 7</Badge>
        )
      }
      bodyClassName="px-2 pt-2 pb-2"
    >
      {loading ? (
        <div className="space-y-2 px-2 py-2" aria-hidden="true">
          {Array.from({ length: 7 }, (_, index) => (
            <div key={index} className="flex items-center gap-2">
              <Skeleton className="h-2.5 w-20" />
              <Skeleton className="h-4 flex-1" />
            </div>
          ))}
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(204, data.length * 27 + 12)}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 2, right: 30, bottom: 2, left: 2 }}
            barCategoryGap={5}
          >
            <CartesianGrid
              horizontal={false}
              stroke={COLORS.grid}
              strokeOpacity={0.5}
              strokeDasharray="3 4"
            />
            <XAxis type="number" hide domain={[0, "dataMax"]} />
            <YAxis
              type="category"
              dataKey="short"
              width={112}
              tick={{ fill: COLORS.muted, fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.03)" }}
              content={<TechniqueTooltip />}
            />
            <Bar
              dataKey="count"
              radius={[0, 4, 4, 0]}
              barSize={13}
              isAnimationActive={false}
              className="cursor-pointer"
              onClick={(entry: unknown) => {
                const record = entry as Partial<Datum> & { payload?: Datum };
                const datum =
                  record.payload ?? (record.id ? (record as Datum) : undefined);
                if (datum?.id) {
                  onSelectTechnique(
                    selectedTechnique === datum.id ? "all" : datum.id,
                  );
                }
              }}
            >
              {data.map((item) => (
                <Cell
                  key={item.id}
                  fill={item.color}
                  fillOpacity={
                    selectedTechnique === "all" || selectedTechnique === item.id
                      ? 0.92
                      : 0.28
                  }
                />
              ))}
              <LabelList
                dataKey="count"
                position="right"
                fill={COLORS.muted}
                fontSize={9}
                fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace"
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Panel>
  );
}
