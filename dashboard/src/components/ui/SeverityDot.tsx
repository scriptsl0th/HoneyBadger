import type { Severity } from "../../types";
import { SEVERITY_LABELS, severityColor, severityTextColor } from "../../lib/severity";

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
        className="size-1.5 shrink-0"
        style={{ backgroundColor: color }}
      />
      {showLabel && (
        <span
          className="font-mono text-[9px] font-medium tracking-[0.08em] uppercase"
          style={{ color: severityTextColor(severity) }}
        >
          {label}
        </span>
      )}
      <span className="sr-only">{label}</span>
    </span>
  );
}
