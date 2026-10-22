import type { ReactNode } from "react";

type Tone =
  | "neutral"
  | "outline"
  | "ssh"
  | "http"
  | "low"
  | "medium"
  | "high"
  | "critical"
  | "success"
  | "warning";

const TONES: Record<Tone, string> = {
  neutral: "border-console-border bg-white/[0.035] text-console-muted",
  outline: "border-console-border bg-transparent text-console-muted",
  ssh: "border-[#8b5cf6]/35 bg-[#8b5cf6]/12 text-[#c4b5fd]",
  http: "border-[#06b6d4]/35 bg-[#06b6d4]/10 text-[#67e8f9]",
  low: "border-[#38bdf8]/35 bg-[#38bdf8]/10 text-[#7dd3fc]",
  medium: "border-[#f59e0b]/35 bg-[#f59e0b]/10 text-[#fcd34d]",
  high: "border-[#f97316]/35 bg-[#f97316]/10 text-[#fdba74]",
  critical: "border-[#ef4444]/40 bg-[#ef4444]/12 text-[#fca5a5]",
  success: "border-[#22c55e]/35 bg-[#22c55e]/10 text-[#86efac]",
  warning: "border-[#f59e0b]/35 bg-[#f59e0b]/10 text-[#fcd34d]",
};

interface BadgeProps {
  children: ReactNode;
  tone?: Tone;
  size?: "xs" | "sm";
  mono?: boolean;
  className?: string;
  title?: string;
}

export function Badge({
  children,
  tone = "neutral",
  size = "xs",
  mono = false,
  className = "",
  title,
}: BadgeProps) {
  return (
    <span
      title={title}
      className={[
        "inline-flex items-center gap-1 rounded border font-medium whitespace-nowrap",
        size === "xs"
          ? "px-1.5 py-0.5 text-[10px] tracking-wide"
          : "px-2 py-0.5 text-[11px]",
        mono ? "font-mono" : "",
        TONES[tone],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </span>
  );
}
