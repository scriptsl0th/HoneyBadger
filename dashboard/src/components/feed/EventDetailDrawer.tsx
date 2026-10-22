import { useEffect, useRef, type ReactNode } from "react";
import type { EventOut } from "../../types";
import {
  eventSummary,
  formatBytes,
  formatExact,
  relativeTime,
} from "../../lib/format";
import { techniqueLabel } from "../../lib/techniques";
import { severityColor } from "../../lib/severity";
import { Badge } from "../ui/Badge";
import { CopyButton } from "../ui/CopyButton";
import { SeverityDot } from "../ui/SeverityDot";

interface EventDetailDrawerProps {
  event: EventOut | null;
  onClose: () => void;
}

function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[92px_minmax(0,1fr)] gap-2 border-b border-console-border/40 py-1.5 last:border-0">
      <dt className="text-[9px] font-medium tracking-[0.1em] text-console-muted uppercase">
        {label}
      </dt>
      <dd className="min-w-0 text-[11px] break-words text-console-text">{children}</dd>
    </div>
  );
}

function Section({
  title,
  children,
  actions,
}: {
  title: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <section className="mt-4">
      <div className="mb-1 flex items-center justify-between gap-2">
        <h3 className="text-[9px] font-semibold tracking-[0.16em] text-console-muted uppercase">
          {title}
        </h3>
        {actions}
      </div>
      <dl className="rounded-lg border border-console-border/70 bg-console-bg/35 px-3 py-1">
        {children}
      </dl>
    </section>
  );
}

function Mono({ children }: { children: ReactNode }) {
  return (
    <span className="font-mono text-[10.5px] break-all text-console-text">
      {children}
    </span>
  );
}

export function EventDetailDrawer({ event, onClose }: EventDetailDrawerProps) {
  const drawerRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!event) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();

    const onKeyDown = (keyboardEvent: KeyboardEvent) => {
      if (keyboardEvent.key === "Escape") {
        keyboardEvent.preventDefault();
        onClose();
        return;
      }
      if (keyboardEvent.key !== "Tab" || !drawerRef.current) return;

      const focusable = Array.from(
        drawerRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((element) => element.offsetParent !== null);
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (keyboardEvent.shiftKey && document.activeElement === first) {
        keyboardEvent.preventDefault();
        last.focus();
      } else if (!keyboardEvent.shiftKey && document.activeElement === last) {
        keyboardEvent.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, [event, onClose]);

  if (!event) return null;

  const geo = event.geo_info;
  const login = event.login_info;
  const json = JSON.stringify(event, null, 2);

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-[#02060f]/70 backdrop-blur-[2px]"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="event-detail-title"
        className="animate-slide-in fixed inset-y-0 right-0 z-50 flex w-full max-w-[480px] flex-col border-l border-console-border bg-console-panel shadow-[-20px_0_60px_-20px_rgba(0,0,0,0.9)] motion-reduce:animate-none"
      >
        <header className="flex items-start justify-between gap-3 border-b border-console-border px-5 py-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[9px] font-semibold tracking-[0.18em] text-console-muted uppercase">
                Event detail
              </span>
              <Badge tone={event.service} size="xs" className="uppercase">
                {event.service}
              </Badge>
              <SeverityDot severity={event.severity} />
            </div>
            <h2
              id="event-detail-title"
              className="mt-1.5 truncate font-mono text-sm text-console-text"
              title={event.source_ip}
            >
              {event.source_ip}
            </h2>
            <p className="mt-0.5 text-[10px] text-console-muted">
              {formatExact(event.timestamp)} · {relativeTime(event.timestamp)}
            </p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close event details"
            className="grid size-7 shrink-0 place-items-center rounded-md border border-console-border text-console-muted transition-colors hover:bg-white/[0.06] hover:text-console-text focus-visible:outline-2 focus-visible:outline-[#38bdf8]"
          >
            <svg viewBox="0 0 16 16" className="size-3.5" fill="none" aria-hidden="true">
              <path
                d="m4 4 8 8M12 4l-8 8"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </header>

        <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-5 pt-4 pb-6">
          <div
            className="rounded-lg border px-3 py-2.5"
            style={{
              borderColor: `${severityColor(event.severity)}55`,
              backgroundColor: `${severityColor(event.severity)}0d`,
            }}
          >
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge tone="outline" mono>
                {event.technique_id ?? "unknown"}
              </Badge>
              <span className="text-[11px] font-medium text-console-text">
                {techniqueLabel(event.technique_id)}
              </span>
            </div>
            <p className="mt-1.5 text-[11px] leading-relaxed break-words text-console-muted">
              {eventSummary(event)}
            </p>
          </div>

          <Section title="Source">
            <DetailRow label="IP">
              <span className="flex items-center gap-2">
                <Mono>{event.source_ip}</Mono>
                <CopyButton value={event.source_ip} label="IP" compact />
              </span>
            </DetailRow>
            <DetailRow label="Country">
              {geo?.country ?? <span className="text-console-muted">—</span>}
            </DetailRow>
            <DetailRow label="Region">
              {geo?.region ?? <span className="text-console-muted">—</span>}
            </DetailRow>
            <DetailRow label="City">
              {geo?.city ?? <span className="text-console-muted">—</span>}
            </DetailRow>
            <DetailRow label="ASN">
              <Mono>{geo?.asn ?? "—"}</Mono>
            </DetailRow>
            <DetailRow label="Coordinates">
              <Mono>
                {geo?.latitude !== null &&
                geo?.latitude !== undefined &&
                geo?.longitude !== null &&
                geo?.longitude !== undefined
                  ? `${geo.latitude.toFixed(4)}, ${geo.longitude.toFixed(4)}`
                  : "—"}
              </Mono>
            </DetailRow>
          </Section>

          {(event.http_method || event.http_path || event.http_status_code) && (
            <Section title="HTTP request">
              <DetailRow label="Method">
                <Mono>{event.http_method ?? "—"}</Mono>
              </DetailRow>
              <DetailRow label="Path">
                <Mono>{event.http_path ?? "—"}</Mono>
              </DetailRow>
              <DetailRow label="Status">
                <Mono>{event.http_status_code ?? "—"}</Mono>
              </DetailRow>
              <DetailRow label="User agent">
                <Mono>{event.user_agent ?? "—"}</Mono>
              </DetailRow>
            </Section>
          )}

          {login && (
            <Section title="Credentials (hash only)">
              <DetailRow label="Username">
                <Mono>{login.username ?? "—"}</Mono>
              </DetailRow>
              <DetailRow label="SHA-256">
                <span className="flex items-start gap-1.5">
                  <Mono>{login.password_hash ?? "—"}</Mono>
                  {login.password_hash && (
                    <CopyButton value={login.password_hash} label="Hash" compact />
                  )}
                </span>
              </DetailRow>
            </Section>
          )}

          {event.command && (
            <Section
              title="Command"
              actions={<CopyButton value={event.command} label="Command" compact />}
            >
              <pre className="scrollbar-thin max-h-40 overflow-auto py-1 font-mono text-[10.5px] leading-relaxed break-all whitespace-pre-wrap text-[#fcd34d]">
                {event.command}
              </pre>
            </Section>
          )}

          {event.payload_url && (
            <Section
              title="Payload metadata"
              actions={
                <CopyButton value={event.payload_url} label="URL" compact />
              }
            >
              <DetailRow label="URL">
                {/* Attacker-controlled: rendered as text, never as a link. */}
                <Mono>{event.payload_url}</Mono>
              </DetailRow>
              <DetailRow label="Hash">
                <Mono>{event.payload_hash ?? "—"}</Mono>
              </DetailRow>
              <DetailRow label="Size">
                <Mono>{formatBytes(event.payload_size)}</Mono>
              </DetailRow>
            </Section>
          )}

          <Section
            title="Raw event"
            actions={<CopyButton value={json} label="JSON" compact />}
          >
            <pre className="scrollbar-thin max-h-72 overflow-auto py-2 font-mono text-[10px] leading-relaxed break-all whitespace-pre-wrap text-console-muted">
              {json}
            </pre>
          </Section>
        </div>

        <footer className="flex items-center justify-between border-t border-console-border px-5 py-2 text-[9px] tracking-wide text-console-muted uppercase">
          <span>Esc to close · Tab cycles focus</span>
          <span className="font-mono normal-case">read-only</span>
        </footer>
      </aside>
    </>
  );
}
