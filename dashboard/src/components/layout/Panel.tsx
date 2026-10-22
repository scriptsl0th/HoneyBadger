import type { ReactNode } from "react";
import { ErrorState } from "../ui/ErrorState";
import { PanelSkeleton } from "../ui/Skeleton";
import { EmptyState } from "../ui/EmptyState";

interface PanelProps {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  empty?: boolean;
  emptyState?: ReactNode;
  className?: string;
  bodyClassName?: string;
  children?: ReactNode;
}

/** Consistent panel chrome + loading / error / empty states. */
export function Panel({
  title,
  subtitle,
  actions,
  loading = false,
  error = null,
  onRetry,
  empty = false,
  emptyState,
  className = "",
  bodyClassName = "",
  children,
}: PanelProps) {
  let content: ReactNode = children;
  if (loading) {
    content = <PanelSkeleton />;
  } else if (error) {
    content = <ErrorState message={error} onRetry={onRetry} />;
  } else if (empty) {
    content =
      emptyState ?? (
        <EmptyState
          title="No data in this window"
          message="Nothing matched the current window or filters."
        />
      );
  }

  return (
    <section
      className={`panel-sheen animate-fade-in flex min-w-0 flex-col overflow-hidden rounded-xl border border-console-border bg-console-panel shadow-[0_12px_35px_-24px_rgba(0,0,0,0.9)] ${className}`}
    >
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-x-3 gap-y-2 border-b border-console-border/70 px-4 py-3">
          <div className="min-w-0">
            {title && (
              <h2 className="truncate text-[11px] font-semibold tracking-[0.14em] text-console-text uppercase">
                {title}
              </h2>
            )}
            {subtitle && (
              <p className="mt-0.5 truncate text-[11px] text-console-muted">
                {subtitle}
              </p>
            )}
          </div>
          {actions && (
            <div className="flex shrink-0 flex-wrap items-center gap-1.5">
              {actions}
            </div>
          )}
        </header>
      )}
      <div className={`min-h-0 flex-1 p-4 ${bodyClassName}`}>{content}</div>
    </section>
  );
}
