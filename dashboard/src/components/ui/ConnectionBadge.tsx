import type { LiveStatus } from "../../ws/client";

const LABELS: Record<LiveStatus, string> = {
  live: "LIVE",
  reconnecting: "RECONNECTING",
  connecting: "RECONNECTING",
  polling: "POLLING",
};

const STYLES: Record<LiveStatus, string> = {
  live: "border-[#22c55e]/40 bg-[#22c55e]/10 text-[#86efac]",
  reconnecting: "border-[#f59e0b]/40 bg-[#f59e0b]/10 text-[#fcd34d]",
  connecting: "border-[#f59e0b]/40 bg-[#f59e0b]/10 text-[#fcd34d]",
  polling: "border-[#38bdf8]/40 bg-[#38bdf8]/10 text-[#7dd3fc]",
};

const DOTS: Record<LiveStatus, string> = {
  live: "bg-[#22c55e] shadow-[0_0_8px_#22c55e]",
  reconnecting: "bg-[#f59e0b] shadow-[0_0_8px_#f59e0b]",
  connecting: "bg-[#f59e0b] shadow-[0_0_8px_#f59e0b]",
  polling: "bg-[#38bdf8] shadow-[0_0_8px_#38bdf8]",
};

interface ConnectionBadgeProps {
  status: LiveStatus;
  attempt?: number;
  className?: string;
}

export function ConnectionBadge({
  status,
  attempt = 0,
  className = "",
}: ConnectionBadgeProps) {
  const label = LABELS[status];
  const title =
    status === "live"
      ? "Live WebSocket stream connected"
      : status === "polling"
        ? "WebSocket unavailable — polling /api/events every 10 s"
        : `Reconnecting to the live stream${attempt > 0 ? ` (attempt ${attempt})` : ""}`;

  return (
    <span
      role="status"
      aria-live="polite"
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold tracking-[0.12em] ${STYLES[status]} ${className}`}
    >
      <span
        aria-hidden="true"
        className={`size-1.5 rounded-full ${DOTS[status]} ${
          status === "live" ? "animate-pulse-soft motion-reduce:animate-none" : ""
        }`}
      />
      {label}
      {status !== "live" && attempt > 0 && (
        <span className="font-mono text-[9px] opacity-70">#{attempt}</span>
      )}
    </span>
  );
}
