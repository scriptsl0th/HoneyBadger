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
  neutral: "border-console-border-strong bg-transparent text-console-muted",
  outline: "border-console-border bg-transparent text-console-muted",
  ssh: "border-[#a78bd1]/45 bg-transparent text-[#c4b1e4]",
  http: "border-[#5fa8c7]/45 bg-transparent text-[#93c8de]",
  low: "border-[#6e93a8]/45 bg-transparent text-[#a5c2d2]",
  medium: "border-[#cfa84f]/45 bg-transparent text-[#e2c47e]",
  high: "border-[#d3764b]/50 bg-transparent text-[#e6a17e]",
  critical: "border-[#d94f4a]/55 bg-transparent text-[#ec8a86]",
  success: "border-[#63d69b]/45 bg-transparent text-[#96e8bd]",
  warning: "border-[#cfa84f]/45 bg-transparent text-[#e2c47e]",
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
        "inline-flex items-center gap-1 border font-medium whitespace-nowrap",
        size === "xs"
          ? "px-1 py-px text-[9px] tracking-[0.06em]"
          : "px-1.5 py-0.5 text-[10px] tracking-wide",
        mono ? "font-mono" : "font-sans",
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
