import { useEffect, useRef, useState } from "react";

interface CopyButtonProps {
  value: string;
  label?: string;
  className?: string;
  compact?: boolean;
}

function fallbackCopy(value: string): boolean {
  try {
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
}

export function CopyButton({
  value,
  label = "Copy",
  className = "",
  compact = false,
}: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(
    () => () => {
      if (timer.current !== undefined) window.clearTimeout(timer.current);
    },
    [],
  );

  const copy = async () => {
    let ok = false;
    try {
      await navigator.clipboard.writeText(value);
      ok = true;
    } catch {
      ok = fallbackCopy(value);
    }
    if (!ok) return;
    setCopied(true);
    if (timer.current !== undefined) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied(false), 1400);
  };

  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        void copy();
      }}
      title={copied ? "Copied" : `${label} to clipboard`}
      aria-label={copied ? "Copied to clipboard" : `${label} to clipboard`}
      className={[
        "inline-flex items-center gap-1 rounded border border-console-border bg-white/[0.03] text-console-muted transition-colors hover:border-console-muted/50 hover:text-console-text focus-visible:outline-2 focus-visible:outline-[#38bdf8]",
        compact ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-1 text-[11px]",
        copied ? "border-[#22c55e]/40 text-[#86efac]" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {copied ? (
        <svg viewBox="0 0 16 16" className="size-3" aria-hidden="true" fill="none">
          <path
            d="m3 8.5 3.2 3L13 4.5"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ) : (
        <svg viewBox="0 0 16 16" className="size-3" aria-hidden="true" fill="none">
          <rect
            x="5.5"
            y="5.5"
            width="8"
            height="8"
            rx="1.4"
            stroke="currentColor"
            strokeWidth="1.3"
          />
          <path
            d="M10.5 5V3.9c0-.8-.6-1.4-1.4-1.4H3.9c-.8 0-1.4.6-1.4 1.4v5.2c0 .8.6 1.4 1.4 1.4H5"
            stroke="currentColor"
            strokeWidth="1.3"
          />
        </svg>
      )}
      <span>{copied ? "Copied" : label}</span>
    </button>
  );
}
