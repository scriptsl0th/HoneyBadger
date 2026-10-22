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
        <svg viewBox="0 0 24 24" className="size-5" fill="none" aria-hidden="true">
          <path
            d="M12 4 3.5 19h17L12 4Z"
            stroke="currentColor"
            strokeWidth="1.3"
            strokeLinejoin="round"
          />
          <path d="M12 9.5v4.2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="12" cy="16.6" r=".9" fill="currentColor" />
        </svg>
      }
      action={
        onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="rounded-md border border-console-border bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-console-text transition-colors hover:bg-white/[0.08] focus-visible:outline-2 focus-visible:outline-[#38bdf8]"
          >
            Retry
          </button>
        ) : undefined
      }
    />
  );
}
