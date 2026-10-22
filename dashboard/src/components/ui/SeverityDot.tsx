import type { Severity } from "../../types";
import {
  SEVERITY_LABELS,
  severityColor,
} from "../../lib/severity";

interface SeverityDotProps {
  severity: Severity | null | undefined;
  showLabel?: boolean;
  className?: string;
}

export function SeverityDot({
  severity,
  showLabel = true,
  className = "",
}: SeverityDotProps) {
  const color = severityColor(severity);
  const label = severity ? SEVERITY_LABELS[severity] : "Unknown";

  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap ${className}`}
      title={label}
    >
      <span
        aria-hidden="true"
        className="size-2 shrink-0 rounded-full"
        style={{
          backgroundColor: color,
          boxShadow: `0 0 7px ${color}80`,
        }}
      />
      {showLabel && (
        <span
          className="text-[10px] font-semibold tracking-[0.08em] uppercase"
          style={{ color }}
        >
          {label}
        </span>
      )}
      <span className="sr-only">{label}</span>
    </span>
  );
}
