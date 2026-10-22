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
  ssh: "border-[#b3a5ce]/45 bg-transparent text-[#c9bde0]",
  http: "border-[#86a6bd]/45 bg-transparent text-[#a3c0d3]",
  low: "border-[#7ba39a]/45 bg-transparent text-[#9dbfb7]",
  medium: "border-[#d9a441]/45 bg-transparent text-[#e2b866]",
  high: "border-[#d1794d]/50 bg-transparent text-[#e3996f]",
  critical: "border-[#cb4b43]/55 bg-transparent text-[#e07770]",
  success: "border-[#93ae79]/45 bg-transparent text-[#aec596]",
  warning: "border-[#d9a441]/45 bg-transparent text-[#e2b866]",
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
