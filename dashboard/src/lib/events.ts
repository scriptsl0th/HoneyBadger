import type { EventOut } from "../types";

/**
 * Stable identity for an EventOut (the backend does not expose a row id).
 * Timestamp + source + service is unique enough for a live feed.
 */
export function eventKey(event: EventOut): string {
  return [
    event.timestamp,
    event.source_ip,
    event.service,
    event.http_method ?? "",
    event.http_path ?? "",
    event.http_status_code ?? "",
    event.command ?? "",
    event.payload_url ?? "",
    event.login_info?.username ?? "",
  ].join("|");
}

/** Sorts newest first, de-duplicates, and keeps at most `limit` events. */
export function mergeEvents(
  current: EventOut[],
  incoming: Iterable<EventOut>,
  limit = 500,
): EventOut[] {
  const byKey = new Map<string, EventOut>();
  for (const event of current) byKey.set(eventKey(event), event);
  for (const event of incoming) byKey.set(eventKey(event), event);
  return [...byKey.values()]
    .sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp))
    .slice(0, limit);
}
