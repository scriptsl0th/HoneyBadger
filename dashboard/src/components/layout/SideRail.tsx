import { useEffect, useState } from "react";
import type { LiveStatus } from "../../ws/client";

const NAV = [
  { id: "overview", index: "01", label: "Overview" },
  { id: "signal", index: "02", label: "Signal" },
  { id: "intel", index: "03", label: "Intelligence" },
  { id: "records", index: "04", label: "Records" },
] as const;

const LED: Record<LiveStatus, string> = {
  live: "bg-[#63d69b]",
  polling: "bg-[#5fa8c7]",
  connecting: "bg-[#cfa84f]",
  reconnecting: "bg-[#cfa84f]",
};

export function SideRail({ status }: { status: LiveStatus }) {
  const [active, setActive] = useState<string>("overview");

  useEffect(() => {
    const sections = NAV.map((item) => document.getElementById(item.id)).filter(
      (element): element is HTMLElement => Boolean(element),
    );
    if (sections.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActive(visible.target.id);
      },
      { rootMargin: "-20% 0px -55% 0px", threshold: [0.05, 0.25, 0.5] },
    );

    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  return (
    <aside
      aria-label="Console sections"
      className="fixed inset-y-0 left-0 z-40 hidden w-[52px] flex-col items-center border-r border-console-border bg-console-panel py-3 lg:flex"
    >
      <a
        href="#overview"
        aria-label="HoneyBadger console, back to overview"
        className="grid size-9 place-items-center border border-console-border bg-console-bg"
      >
        <svg viewBox="0 0 32 32" className="size-5" aria-hidden="true">
          <path
            d="M16 2.8 27.4 9.4v13.2L16 29.2 4.6 22.6V9.4Z"
            fill="none"
            stroke="#72e3a4"
            strokeWidth="1.3"
          />
          <path d="M16 9.6 21.8 13v6.2L16 22.4l-5.8-3.2V13Z" fill="#72e3a4" />
          <path d="M16 13.7 18.7 15.2v3.1L16 19.8l-2.7-1.5v-3.1Z" fill="#080b0d" />
        </svg>
      </a>

      <nav className="mt-5 flex flex-col items-center gap-1.5" aria-label="Jump to section">
        {NAV.map((item) => {
          const isActive = active === item.id;
          return (
            <a
              key={item.id}
              href={`#${item.id}`}
              title={item.label}
              aria-label={item.label}
              aria-current={isActive ? "true" : undefined}
              className={[
                "grid size-8 place-items-center border font-mono text-[9px] tracking-wider transition-colors",
                isActive
                  ? "border-console-border-strong bg-console-panel-2 text-console-accent"
                  : "border-transparent text-console-faint hover:border-console-border hover:text-console-text",
              ].join(" ")}
            >
              {item.index}
            </a>
          );
        })}
      </nav>

      <div className="mt-auto flex flex-col items-center gap-3">
        <span
          aria-hidden="true"
          className="[writing-mode:vertical-rl] rotate-180 font-mono text-[8.5px] tracking-[0.32em] text-console-faint uppercase select-none"
        >
          HoneyBadger · HB-01
        </span>
        <span
          className={`size-1.5 ${LED[status]} ${
            status === "live" ? "animate-pulse-soft motion-reduce:animate-none" : ""
          }`}
          title={`Telemetry: ${status}`}
        />
      </div>
    </aside>
  );
}
