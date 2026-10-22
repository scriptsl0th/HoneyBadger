import type { SourceCount } from "../../types";
import { relativeTime } from "../../lib/format";
import { Panel } from "../layout/Panel";
import { EmptyState } from "../ui/EmptyState";

interface TopSourcesProps {
  sources: SourceCount[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function TopSources({ sources, loading, error, onRetry }: TopSourcesProps) {
  return (
    <Panel
      title="Top sources"
      subtitle="Origin IP · ASN · event volume"
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={!loading && !error && (sources?.length ?? 0) === 0}
      emptyState={
        <EmptyState
          title="No source IPs"
          message="Attacker addresses will be ranked here once traffic arrives."
        />
      }
      bodyClassName="p-0"
      className="h-full"
    >
      <ol className="scrollbar-thin max-h-[352px] divide-y divide-console-border/50 overflow-y-auto">
        {(sources ?? []).map((source, index) => (
          <li
            key={source.source_ip}
            className="flex items-start gap-2 px-3 py-2.5 transition-colors hover:bg-white/[0.025]"
          >
            <span className="mt-0.5 w-4 shrink-0 font-mono text-[9px] text-console-muted/70 tabular-nums">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div className="min-w-0 flex-1">
              <p
                className="truncate font-mono text-[11px] text-console-text"
                title={source.source_ip}
              >
                {source.source_ip}
              </p>
              <p
                className="mt-0.5 truncate text-[9.5px] text-console-muted"
                title={[source.country, source.city, source.asn]
                  .filter(Boolean)
                  .join(" · ")}
              >
                {source.country ?? "Unknown"}
                {source.city ? ` · ${source.city}` : ""}
                {source.asn ? ` · ${source.asn}` : ""}
              </p>
            </div>
            <div className="shrink-0 text-right">
              <div className="font-mono text-[11px] font-semibold text-console-text tabular-nums">
                {source.count}
              </div>
              <div className="mt-0.5 text-[9px] whitespace-nowrap text-console-muted">
                {relativeTime(source.last_seen)}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </Panel>
  );
}
