import type { ReactNode } from "react";
import { ErrorState } from "../ui/ErrorState";
import { PanelSkeleton } from "../ui/Skeleton";
import { EmptyState } from "../ui/EmptyState";

interface PanelProps {
  title?: ReactNode;
  subtitle?: ReactNode;
  /** Instrument index, e.g. "03". Rendered before the title. */
  index?: string;
  actions?: ReactNode;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  empty?: boolean;
  emptyState?: ReactNode;
  className?: string;
  bodyClassName?: string;
  id?: string;
  children?: ReactNode;
}

/** Flat instrument module: hairline rule, ink surface, labelled header rail. */
export function Panel({
  title,
  subtitle,
  index,
  actions,
  loading = false,
  error = null,
  onRetry,
  empty = false,
  emptyState,
  className = "",
  bodyClassName = "",
  id,
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
      id={id}
      className={`animate-fade-in flex min-w-0 flex-col border border-console-border bg-console-panel ${className}`}
    >
      {(title || actions) && (
        <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-b border-console-border bg-console-panel-2 px-3 py-2">
          <div className="min-w-0">
            {title && (
              <div className="flex min-w-0 items-baseline gap-2">
                {index && (
                  <span
                    aria-hidden="true"
                    className="font-mono text-[9px] leading-none font-medium text-console-accent"
                  >
                    {index}
                  </span>
                )}
                <h2 className="label truncate text-console-text">{title}</h2>
              </div>
            )}
            {subtitle && (
              <p className="mt-1 truncate text-[10.5px] leading-tight text-console-muted">
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
      <div
        className={
          bodyClassName
            ? `min-h-0 flex-1 ${bodyClassName}`
            : "min-h-0 flex-1 p-3"
        }
      >
        {content}
      </div>
    </section>
  );
}
