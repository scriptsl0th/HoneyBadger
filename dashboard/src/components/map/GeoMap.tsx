import { useMemo, useState, type MouseEvent } from "react";
import { geoEqualEarth, geoGraticule10, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { FeatureCollection, Geometry } from "geojson";
import worldData from "world-atlas/countries-110m.json";
import type { EventOut, Service, Severity, SourceCount } from "../../types";
import { COLORS, serviceColor } from "../../lib/colors";
import { severityColor, severityRank } from "../../lib/severity";
import { compactNumber } from "../../lib/format";
import { Panel } from "../layout/Panel";
import { SeverityDot } from "../ui/SeverityDot";

const WIDTH = 920;
const HEIGHT = 470;

type WorldTopology = Parameters<typeof feature>[0];
interface WorldObject {
  objects: { countries: Parameters<typeof feature>[1] };
}

interface Bubble {
  ip: string;
  x: number;
  y: number;
  radius: number;
  color: string;
  severity: Severity | null;
  service: Service | null;
  count: number;
  country: string | null;
  city: string | null;
  asn: string | null;
}

interface HoverState {
  bubble: Bubble;
  x: number;
  y: number;
}

interface GeoMapProps {
  sources: SourceCount[] | null;
  events: EventOut[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function GeoMap({
  sources,
  events,
  loading,
  error,
  onRetry,
}: GeoMapProps) {
  const [hover, setHover] = useState<HoverState | null>(null);

  const projection = useMemo(() => {
    const next = geoEqualEarth();
    next.fitSize([WIDTH, HEIGHT], { type: "Sphere" } as never);
    return next;
  }, []);

  const path = useMemo(() => geoPath(projection), [projection]);

  const countries = useMemo(() => {
    const topology = worldData as unknown as WorldTopology & WorldObject;
    return feature(
      topology,
      topology.objects.countries,
    ) as unknown as FeatureCollection<Geometry>;
  }, []);

  const countryPaths = useMemo(
    () =>
      countries.features
        .map((country) => path(country))
        .filter((value): value is string => Boolean(value)),
    [countries, path],
  );

  const spherePath = useMemo(() => path({ type: "Sphere" } as never) ?? "", [path]);
  const graticulePath = useMemo(() => path(geoGraticule10()) ?? "", [path]);

  const eventMeta = useMemo(() => {
    const map = new Map<
      string,
      { severity: Severity | null; service: Service | null }
    >();
    for (const event of events) {
      const current = map.get(event.source_ip);
      const severity =
        severityRank(event.severity) > severityRank(current?.severity)
          ? event.severity
          : (current?.severity ?? null);
      map.set(event.source_ip, {
        severity,
        service: current?.service ?? event.service,
      });
    }
    return map;
  }, [events]);

  const bubbles: Bubble[] = useMemo(() => {
    const located = (sources ?? []).filter(
      (source) =>
        source.latitude !== null &&
        source.longitude !== null &&
        Number.isFinite(source.latitude) &&
        Number.isFinite(source.longitude),
    );
    const max = Math.max(1, ...located.map((source) => source.count));

    return located
      .map((source) => {
        const point = projection([source.longitude ?? 0, source.latitude ?? 0]);
        if (!point) return null;
        const meta = eventMeta.get(source.source_ip);
        const severity = meta?.severity ?? null;
        return {
          ip: source.source_ip,
          x: point[0],
          y: point[1],
          radius: 3 + Math.sqrt(source.count / max) * 10,
          color: severity
            ? severityColor(severity)
            : meta?.service
              ? serviceColor(meta.service)
              : COLORS.http,
          severity,
          service: meta?.service ?? null,
          count: source.count,
          country: source.country,
          city: source.city,
          asn: source.asn,
        } satisfies Bubble;
      })
      .filter((bubble): bubble is Bubble => bubble !== null)
      .sort((a, b) => b.count - a.count);
  }, [sources, projection, eventMeta, events]);

  const empty = !loading && !error && bubbles.length === 0;

  const showHover = (event: MouseEvent<SVGCircleElement>, bubble: Bubble) => {
    const svg = event.currentTarget.ownerSVGElement;
    if (!svg) return;
    const box = svg.getBoundingClientRect();
    setHover({
      bubble,
      x: ((event.clientX - box.left) / box.width) * WIDTH,
      y: ((event.clientY - box.top) / box.height) * HEIGHT,
    });
  };

  return (
    <Panel
      title="Attack origins"
      subtitle={
        sources
          ? `${bubbles.length} geolocated sources · bubble size = events`
          : "Geolocation of attacking sources"
      }
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={empty}
      emptyState={
        <div className="flex h-[300px] flex-col items-center justify-center gap-1.5 text-center">
          <span className="text-sm font-medium text-console-text">
            No geolocated sources
          </span>
          <span className="max-w-xs text-xs text-console-muted">
            Top sources in this window have no latitude/longitude enrichment.
          </span>
        </div>
      }
      actions={
        <div className="flex items-center gap-2.5" aria-label="Severity legend">
          {(
            [
              ["high", COLORS.high],
              ["critical", COLORS.critical],
              ["medium", COLORS.medium],
            ] as const
          ).map(([label, color]) => (
            <span
              key={label}
              className="inline-flex items-center gap-1 text-[9px] tracking-wide text-console-muted uppercase"
            >
              <span
                className="size-1.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              {label}
            </span>
          ))}
        </div>
      }
      bodyClassName="relative flex items-center p-0"
      className="h-full"
    >
      <div className="relative w-full">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-auto w-full"
          role="img"
          aria-label={`World map with ${bubbles.length} attack origin bubbles`}
          onMouseLeave={() => setHover(null)}
        >
          <defs>
            <radialGradient id="ocean-glow" cx="50%" cy="42%" r="62%">
              <stop offset="0%" stopColor="#13223b" stopOpacity={0.82} />
              <stop offset="100%" stopColor="#0c1526" stopOpacity={0.92} />
            </radialGradient>
          </defs>

          <path d={spherePath} fill="url(#ocean-glow)" />
          <path
            d={graticulePath}
            fill="none"
            stroke={COLORS.border}
            strokeWidth={0.5}
            strokeOpacity={0.4}
          />

          {countryPaths.map((d, index) => (
            <path
              key={index}
              d={d}
              fill="#101b2e"
              stroke="#263656"
              strokeWidth={0.45}
              strokeOpacity={0.9}
            />
          ))}

          <path
            d={spherePath}
            fill="none"
            stroke="#2b3d60"
            strokeWidth={0.8}
            strokeOpacity={0.6}
          />

          {bubbles.map((bubble) => (
            <g key={bubble.ip}>
              <circle
                cx={bubble.x}
                cy={bubble.y}
                r={bubble.radius + 4}
                fill={bubble.color}
                fillOpacity={0.1}
                className={
                  bubble.severity === "critical"
                    ? "animate-pulse-soft motion-reduce:animate-none"
                    : undefined
                }
              />
              <circle
                cx={bubble.x}
                cy={bubble.y}
                r={bubble.radius}
                fill={bubble.color}
                fillOpacity={0.7}
                stroke={bubble.color}
                strokeWidth={1}
                strokeOpacity={0.9}
                tabIndex={0}
                role="button"
                aria-label={`${bubble.ip}, ${bubble.country ?? "unknown country"}, ${bubble.count} events`}
                className="cursor-pointer focus-visible:stroke-white focus-visible:outline-none"
                onMouseEnter={(event) => showHover(event, bubble)}
                onFocus={() => setHover({ bubble, x: bubble.x, y: bubble.y - 6 })}
                onBlur={() => setHover(null)}
              />
            </g>
          ))}

        </svg>

        <div className="pointer-events-none absolute bottom-2 left-3 rounded border border-console-border/70 bg-console-bg/70 px-2 py-1 text-[9px] text-console-muted backdrop-blur">
          Equal Earth · no external tiles
        </div>

        {hover && (
          <div
            className="pointer-events-none absolute z-10 hidden w-48 -translate-x-1/2 -translate-y-[calc(100%+8px)] rounded-lg border border-console-border bg-[#0a1220]/95 px-3 py-2 shadow-xl backdrop-blur sm:block"
            style={{
              left: `${(hover.x / WIDTH) * 100}%`,
              top: `${(hover.y / HEIGHT) * 100}%`,
            }}
          >
            <div className="font-mono text-[10px] text-console-text">
              {hover.bubble.ip}
            </div>
            <div className="mt-0.5 text-[10px] text-console-muted">
              {hover.bubble.country ?? "Unknown"}
              {hover.bubble.city ? ` · ${hover.bubble.city}` : ""}
            </div>
            <div className="mt-0.5 text-[10px] text-console-muted">
              {hover.bubble.asn ?? "ASN unknown"}
            </div>
            <div className="mt-1 flex items-center justify-between border-t border-console-border/60 pt-1">
              <SeverityDot severity={hover.bubble.severity} />
              <span className="font-mono text-[10px] text-console-text">
                {compactNumber(hover.bubble.count)} events
              </span>
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
}
