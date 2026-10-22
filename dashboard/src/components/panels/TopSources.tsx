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
      index="04.2"
      title="Origin sources"
      subtitle="Attacker IP · ASN · event volume"
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
      <ol className="scrollbar-thin max-h-[352px] divide-y divide-console-border/55 overflow-y-auto">
        {(sources ?? []).map((source, index) => (
          <li
            key={source.source_ip}
            className="flex items-start gap-2 px-3 py-2 transition-colors hover:bg-white/[0.025]"
          >
            <span className="mt-0.5 w-5 shrink-0 font-mono text-[8.5px] text-console-faint tabular-nums">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div className="min-w-0 flex-1">
              <p
                className="truncate font-mono text-[10px] leading-tight text-console-text"
                title={source.source_ip}
              >
                {source.source_ip}
              </p>
              <p
                className="mt-1 truncate text-[9px] text-console-muted"
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
              <div className="font-mono text-[11px] leading-none font-medium text-console-text tabular-nums">
                {source.count}
              </div>
              <div className="mt-1 font-mono text-[8.5px] whitespace-nowrap text-console-faint">
                {relativeTime(source.last_seen)}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </Panel>
  );
}
