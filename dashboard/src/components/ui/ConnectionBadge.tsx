import type { LiveStatus } from "../../ws/client";

const LABELS: Record<LiveStatus, string> = {
  live: "LIVE",
  reconnecting: "RECONNECT",
  connecting: "CONNECTING",
  polling: "POLLING",
};

const LED: Record<LiveStatus, string> = {
  live: "bg-[#63d69b]",
  reconnecting: "bg-[#cfa84f]",
  connecting: "bg-[#cfa84f]",
  polling: "bg-[#5fa8c7]",
};

const TEXT: Record<LiveStatus, string> = {
  live: "text-console-live",
  reconnecting: "text-console-accent",
  connecting: "text-console-accent",
  polling: "text-[#93c8de]",
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
      className={`inline-flex items-center gap-1.5 border border-console-border bg-console-panel px-2 py-1.5 ${className}`}
    >
      <span
        aria-hidden="true"
        className={`size-1.5 ${LED[status]} ${
          status === "live" ? "animate-pulse-soft motion-reduce:animate-none" : ""
        }`}
      />
      <span
        className={`font-mono text-[9px] leading-none font-medium tracking-[0.12em] ${TEXT[status]}`}
      >
        {label}
      </span>
      {status !== "live" && attempt > 0 && (
        <span className="font-mono text-[9px] leading-none text-console-faint">
          #{attempt}
        </span>
      )}
    </span>
  );
}
