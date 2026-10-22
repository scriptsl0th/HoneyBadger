import { useEffect, useState } from "react";

function utcTime(date: Date): string {
  return date.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
}

/** Wall clock readout. The console reports all telemetry in UTC. */
export function UtcClock() {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="hidden items-baseline gap-1 md:flex" title="Coordinated Universal Time">
      <span className="font-mono text-[11px] leading-none text-console-text tabular-nums">
        {utcTime(now)}
      </span>
      <span className="font-mono text-[8.5px] leading-none tracking-[0.14em] text-console-faint">
        UTC
      </span>
    </div>
  );
}
