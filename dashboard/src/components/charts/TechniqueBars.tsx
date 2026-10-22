import { useMemo } from "react";
import type { TechniqueCount } from "../../types";
import { techniqueLabel } from "../../lib/techniques";
import { compactNumber } from "../../lib/format";
import { Panel } from "../layout/Panel";
import { Skeleton } from "../ui/Skeleton";

interface TechniqueBarsProps {
  techniques: TechniqueCount[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  selectedTechnique: string;
  onSelectTechnique: (technique: string) => void;
}

export function TechniqueBars({
  techniques,
  loading,
  error,
  onRetry,
  selectedTechnique,
  onSelectTechnique,
}: TechniqueBarsProps) {
  const data = useMemo(
    () =>
      [...(techniques ?? [])].sort((a, b) => b.count - a.count).slice(0, 7),
    [techniques],
  );

  const total = (techniques ?? []).reduce((sum, item) => sum + item.count, 0);
  const max = Math.max(1, ...data.map((item) => item.count));
  const empty = !loading && !error && total === 0;

  return (
    <Panel
      index="02.2"
      title="ATT&CK coverage"
      subtitle={
        selectedTechnique === "all"
          ? "Classified volume · select a row to filter the feed"
          : `Feed filtered to ${selectedTechnique}`
      }
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={empty}
      emptyState={
        <div className="flex h-[196px] flex-col items-center justify-center gap-1.5 text-center">
          <span className="font-mono text-[10px] tracking-[0.16em] text-console-faint uppercase">
            No classifications
          </span>
          <span className="max-w-[240px] text-[11px] text-console-muted">
            Events will appear here as they are tagged against ATT&amp;CK.
          </span>
        </div>
      }
      actions={
        selectedTechnique !== "all" ? (
          <button
            type="button"
            onClick={() => onSelectTechnique("all")}
            className="border border-console-border px-1.5 py-0.5 font-mono text-[9px] tracking-[0.06em] text-console-muted uppercase transition-colors hover:border-console-border-strong hover:text-console-text"
          >
            Clear
          </button>
        ) : (
          <span className="font-mono text-[9px] tracking-[0.1em] text-console-faint">
            TOP 7
          </span>
        )
      }
      bodyClassName="p-0"
    >
      {loading ? (
        <div className="space-y-2 p-3" aria-hidden="true">
          {Array.from({ length: 7 }, (_, index) => (
            <div key={index} className="flex items-center gap-2">
              <Skeleton className="h-2.5 w-12" />
              <Skeleton className="h-3 flex-1" />
            </div>
          ))}
        </div>
      ) : (
        <ol className="divide-y divide-console-border/60">
          {data.map((item) => {
            const selected = selectedTechnique === item.technique_id;
            const share = total > 0 ? (item.count / total) * 100 : 0;
            return (
              <li key={item.technique_id}>
                <button
                  type="button"
                  onClick={() =>
                    onSelectTechnique(
                      selected ? "all" : item.technique_id,
                    )
                  }
                  aria-pressed={selected}
                  className={[
                    "group grid w-full grid-cols-[52px_minmax(0,1fr)_44px] items-center gap-x-2 border-l-2 px-2 py-1.5 text-left transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-console-accent",
                    selected
                      ? "border-console-accent bg-console-panel-2"
                      : "border-transparent hover:bg-white/[0.025]",
                  ].join(" ")}
                >
                  <span
                    className={`font-mono text-[9px] leading-none tracking-[0.02em] ${
                      selected ? "text-console-accent" : "text-console-faint"
                    }`}
                  >
                    {item.technique_id}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-[10px] leading-tight text-console-muted group-hover:text-console-text">
                      {techniqueLabel(item.technique_id)}
                    </span>
                    <span
                      aria-hidden="true"
                      className="mt-1 block h-[3px] w-full bg-console-bg"
                    >
                      <span
                        className={`block h-full ${
                          selected
                            ? "bg-console-accent"
                            : "bg-console-accent/55 group-hover:bg-console-accent/80"
                        }`}
                        style={{ width: `${Math.max(3, (item.count / max) * 100)}%` }}
                      />
                    </span>
                  </span>
                  <span className="text-right">
                    <span className="block font-mono text-[10px] leading-none text-console-text tabular-nums">
                      {compactNumber(item.count)}
                    </span>
                    <span className="mt-0.5 block font-mono text-[8.5px] leading-none text-console-faint tabular-nums">
                      {share.toFixed(1)}%
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </Panel>
  );
}
