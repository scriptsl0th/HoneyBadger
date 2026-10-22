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
      <span
        aria-hidden="true"
        className="grid size-9 place-items-center border border-console-border text-console-faint"
      >
        {icon ?? (
          <svg viewBox="0 0 24 24" className="size-4" fill="none">
            <path d="M12 3.5v17M3.5 12h17" stroke="currentColor" strokeWidth="1" />
            <rect x="8" y="8" width="8" height="8" stroke="currentColor" strokeWidth="1" />
          </svg>
        )}
      </span>
      <div className="space-y-1">
        <p className="text-[12px] font-medium text-console-text">{title}</p>
        <p className="mx-auto max-w-sm text-[10.5px] leading-relaxed text-console-muted">
          {message}
        </p>
      </div>
      {command && (
        <div className="flex w-full max-w-md items-center gap-2 border border-console-border bg-console-bg px-2 py-1.5">
          <span aria-hidden="true" className="font-mono text-[10px] text-console-accent">
            $
          </span>
          <code className="scrollbar-thin min-w-0 flex-1 overflow-x-auto text-left font-mono text-[10.5px] whitespace-nowrap text-console-muted">
            {command}
          </code>
          <CopyButton value={command} label="Copy" compact />
        </div>
      )}
      {action}
    </div>
  );
}
