import { memo } from "react";
import type { EventOut } from "../../types";
import { eventSummary, formatClock, formatExact, truncate } from "../../lib/format";
import { techniqueLabel } from "../../lib/techniques";
import { Badge } from "../ui/Badge";
import { SeverityDot } from "../ui/SeverityDot";

interface EventRowProps {
  event: EventOut;
  onSelect: (event: EventOut) => void;
}

export const EventRow = memo(function EventRow({ event, onSelect }: EventRowProps) {
  const summary = eventSummary(event);
  const technique = event.technique_id ?? "—";

  return (
    <tr
      tabIndex={0}
      aria-label={`${formatClock(event.timestamp)} ${event.service} event from ${event.source_ip}`}
      onClick={() => onSelect(event)}
      onKeyDown={(keyboardEvent) => {
        if (keyboardEvent.key === "Enter" || keyboardEvent.key === " ") {
          keyboardEvent.preventDefault();
          onSelect(event);
        }
      }}
      className="group cursor-pointer border-b border-console-border/45 transition-colors last:border-0 hover:bg-white/[0.035] focus-visible:bg-white/[0.05] focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-[#38bdf8]"
    >
      <td className="py-1.5 pr-1 pl-2 align-middle whitespace-nowrap">
        <time
          dateTime={event.timestamp}
          title={formatExact(event.timestamp)}
          className="font-mono text-[10px] text-console-muted tabular-nums"
        >
          {formatClock(event.timestamp)}
        </time>
      </td>
      <td className="py-1.5 align-middle">
        <Badge tone={event.service} size="xs" className="uppercase">
          {event.service}
        </Badge>
      </td>
      <td className="max-w-[108px] py-1.5 align-middle">
        <span
          className="block truncate font-mono text-[10.5px] text-console-text"
          title={event.source_ip}
        >
          {event.source_ip}
        </span>
      </td>
      <td className="hidden py-1.5 align-middle 2xl:table-cell">
        <span
          className="block max-w-[76px] truncate text-[10px] text-console-muted"
          title={[event.geo_info?.country, event.geo_info?.city]
            .filter(Boolean)
            .join(" · ")}
        >
          {event.geo_info?.country ?? "—"}
        </span>
      </td>
      <td className="py-1 pr-1 align-middle">
        <span className="flex max-w-[96px] flex-col items-start gap-0.5">
          <Badge tone="outline" mono size="xs" title={techniqueLabel(technique)}>
            {technique}
          </Badge>
          <span
            className="w-full truncate text-[9px] leading-tight text-console-muted"
            title={techniqueLabel(technique)}
          >
            {techniqueLabel(technique)}
          </span>
        </span>
      </td>
      <td className="py-1.5 pr-1 align-middle">
        <SeverityDot severity={event.severity} />
      </td>
      <td className="py-1.5 pr-2 align-middle">
        <span
          className="line-clamp-2 text-[10px] leading-snug text-console-muted group-hover:text-console-text"
          title={summary}
        >
          {truncate(summary, 88)}
        </span>
      </td>
    </tr>
  );
});
