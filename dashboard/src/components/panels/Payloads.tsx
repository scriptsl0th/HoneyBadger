import type { PayloadCount } from "../../types";
import { formatBytes, relativeTime, shortHash } from "../../lib/format";
import { Panel } from "../layout/Panel";
import { Badge } from "../ui/Badge";
import { EmptyState } from "../ui/EmptyState";

interface PayloadsProps {
  payloads: PayloadCount[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function Payloads({ payloads, loading, error, onRetry }: PayloadsProps) {
  return (
    <Panel
      index="04.3"
      title="Payload references"
      subtitle="Metadata only — never fetched or executed"
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={!loading && !error && (payloads?.length ?? 0) === 0}
      emptyState={
        <EmptyState
          title="No payloads observed"
          message="Ingress tool transfer attempts will be listed here as plain-text URLs."
        />
      }
      bodyClassName="p-0"
      className="h-full"
    >
      <ul className="scrollbar-thin max-h-[352px] divide-y divide-console-border/55 overflow-y-auto">
        {(payloads ?? []).map((payload) => (
          <li
            key={payload.url}
            className="px-3 py-2 transition-colors hover:bg-white/[0.025]"
          >
            <div className="flex items-start justify-between gap-2">
              {/* Attacker-controlled string: text only, deliberately not a link. */}
              <p
                className="min-w-0 flex-1 font-mono text-[9.5px] leading-relaxed break-all text-console-text"
                title={payload.url}
              >
                {payload.url}
              </p>
              {payload.quarantined && (
                <Badge tone="warning" className="shrink-0 uppercase">
                  Held
                </Badge>
              )}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-[8.5px] text-console-faint">
              <span>{formatBytes(payload.size)}</span>
              <span aria-hidden="true" className="text-console-border-strong">
                /
              </span>
              <span title={payload.hash ?? undefined}>
                {payload.hash ? shortHash(payload.hash, 12, 4) : "no hash"}
              </span>
              <span aria-hidden="true" className="text-console-border-strong">
                /
              </span>
              <span>{relativeTime(payload.first_seen)}</span>
            </div>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
