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
        "inline-flex items-center gap-1 border border-console-border bg-transparent font-mono tracking-[0.04em] text-console-faint transition-colors hover:border-console-border-strong hover:text-console-text focus-visible:outline-2 focus-visible:outline-console-accent",
        compact ? "px-1 py-0.5 text-[9px]" : "px-1.5 py-1 text-[10px]",
        copied ? "border-console-live/50 text-console-live" : "",
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
            strokeWidth="1.6"
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
            stroke="currentColor"
            strokeWidth="1.2"
          />
          <path
            d="M10.5 5V3.9c0-.8-.6-1.4-1.4-1.4H3.9c-.8 0-1.4.6-1.4 1.4v5.2c0 .8.6 1.4 1.4 1.4H5"
            stroke="currentColor"
            strokeWidth="1.2"
          />
        </svg>
      )}
      <span>{copied ? "Copied" : label}</span>
    </button>
  );
}
