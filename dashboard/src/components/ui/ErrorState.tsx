import { EmptyState } from "./EmptyState";

interface ErrorStateProps {
  message?: string | null;
  onRetry?: () => void;
  title?: string;
}

export function ErrorState({
  message,
  onRetry,
  title = "Telemetry unavailable",
}: ErrorStateProps) {
  return (
    <EmptyState
      title={title}
      message={message ?? "The dashboard could not reach the HoneyBadger API."}
      icon={
        <svg viewBox="0 0 24 24" className="size-4" fill="none" aria-hidden="true">
          <path
            d="M12 4 3.5 19h17L12 4Z"
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinejoin="round"
          />
          <path d="M12 9.5v4.2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          <circle cx="12" cy="16.6" r=".9" fill="currentColor" />
        </svg>
      }
      action={
        onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="border border-console-border-strong bg-console-panel px-3 py-1.5 font-mono text-[10px] tracking-[0.08em] text-console-text uppercase transition-colors hover:border-console-muted focus-visible:outline-2 focus-visible:outline-console-accent"
          >
            Retry
          </button>
        ) : undefined
      }
    />
  );
}
