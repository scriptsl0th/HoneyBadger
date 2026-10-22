import type { ReactNode } from "react";
import { CopyButton } from "./CopyButton";

interface EmptyStateProps {
  title: string;
  message: string;
  command?: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  message,
  command,
  icon,
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 px-4 py-10 text-center ${className}`}
    >
      <span className="grid size-11 place-items-center rounded-full border border-console-border bg-white/[0.03] text-console-muted">
        {icon ?? (
          <svg viewBox="0 0 24 24" className="size-5" fill="none" aria-hidden="true">
            <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.3" />
            <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.3" opacity=".55" />
            <circle cx="12" cy="12" r="1.25" fill="currentColor" />
            <path d="M12 3.5V6M12 18v2.5M3.5 12H6M18 12h2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
        )}
      </span>
      <div className="space-y-1">
        <p className="text-sm font-medium text-console-text">{title}</p>
        <p className="mx-auto max-w-sm text-xs leading-relaxed text-console-muted">
          {message}
        </p>
      </div>
      {command && (
        <div className="flex w-full max-w-md items-center gap-2 rounded-lg border border-console-border bg-console-bg/70 px-2.5 py-2">
          <code className="scrollbar-thin min-w-0 flex-1 overflow-x-auto text-left font-mono text-[11px] whitespace-nowrap text-[#7dd3fc]">
            {command}
          </code>
          <CopyButton value={command} label="Copy" compact />
        </div>
      )}
      {action}
    </div>
  );
}
