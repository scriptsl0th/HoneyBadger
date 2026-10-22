import type { ServiceCount } from "../../types";
import { serviceColor, serviceLabel } from "../../lib/colors";
import { compactNumber } from "../../lib/format";
import { Panel } from "../layout/Panel";
import { Skeleton } from "../ui/Skeleton";

interface ServiceSplitProps {
  services: ServiceCount[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function ServiceSplit({
  services,
  loading,
  error,
  onRetry,
}: ServiceSplitProps) {
  const rows = (services ?? []).filter((item) => item.count > 0);
  const total = rows.reduce((sum, item) => sum + item.count, 0);
  const empty = !loading && !error && total === 0;

  return (
    <Panel
      index="02.3"
      title="Service split"
      subtitle="SSH :8022 vs HTTP :8081"
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={empty}
      emptyState={
        <div className="flex h-[132px] flex-col items-center justify-center gap-1.5 text-center">
          <span className="font-mono text-[10px] tracking-[0.16em] text-console-faint uppercase">
            No protocol data
          </span>
          <span className="text-[11px] text-console-muted">
            Waiting for SSH or HTTP honeypot traffic.
          </span>
        </div>
      }
      bodyClassName="p-0"
    >
      {loading ? (
        <div className="space-y-3 p-3" aria-hidden="true">
          <Skeleton className="h-7 w-24" />
          <Skeleton className="h-2 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
        </div>
      ) : (
        <div className="p-3">
          <div className="flex items-baseline justify-between">
            <span className="font-display text-[24px] leading-none font-semibold text-console-text tabular-nums">
              {compactNumber(total)}
            </span>
            <span className="font-mono text-[9px] tracking-[0.12em] text-console-faint uppercase">
              events
            </span>
          </div>

          <div
            className="mt-3 flex h-2 w-full gap-px bg-console-border"
            role="img"
            aria-label={rows
              .map(
                (item) =>
                  `${serviceLabel(item.service)} ${Math.round((item.count / total) * 100)} percent`,
              )
              .join(", ")}
          >
            {rows.map((item) => (
              <span
                key={item.service}
                className="h-full"
                style={{
                  width: `${(item.count / total) * 100}%`,
                  backgroundColor: serviceColor(item.service),
                  opacity: 0.85,
                }}
              />
            ))}
          </div>

          <dl className="mt-3 divide-y divide-console-border/60 border-t border-console-border/60">
            {rows.map((item) => {
              const percent = total > 0 ? (item.count / total) * 100 : 0;
              return (
                <div
                  key={item.service}
                  className="flex items-center gap-2 py-1.5"
                >
                  <span
                    aria-hidden="true"
                    className="size-1.5 shrink-0"
                    style={{ backgroundColor: serviceColor(item.service) }}
                  />
                  <dt className="font-mono text-[9px] tracking-[0.1em] text-console-muted uppercase">
                    {serviceLabel(item.service)}
                  </dt>
                  <dd className="ml-auto flex items-baseline gap-2 font-mono text-[10px] tabular-nums">
                    <span className="text-console-text">{compactNumber(item.count)}</span>
                    <span className="w-9 text-right text-console-faint">
                      {percent.toFixed(0)}%
                    </span>
                  </dd>
                </div>
              );
            })}
          </dl>
        </div>
      )}
    </Panel>
  );
}
