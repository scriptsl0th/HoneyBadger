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
          radius: 2.6 + Math.sqrt(source.count / max) * 8,
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
      index="03.1"
      title="Attack origins"
      subtitle={
        sources
          ? `${bubbles.length} geolocated sources · area = event volume`
          : "Geolocation of attacking sources"
      }
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={empty}
      emptyState={
        <div className="flex h-[300px] flex-col items-center justify-center gap-1.5 text-center">
          <span className="font-mono text-[10px] tracking-[0.16em] text-console-faint uppercase">
            No geolocated sources
          </span>
          <span className="max-w-xs text-[11px] text-console-muted">
            Top sources in this window have no latitude/longitude enrichment.
          </span>
        </div>
      }
      actions={
        <div className="flex items-center gap-2.5" aria-label="Severity legend">
          {(
            [
              ["low", COLORS.low],
              ["med", COLORS.medium],
              ["high", COLORS.high],
              ["crit", COLORS.critical],
            ] as const
          ).map(([label, color]) => (
            <span
              key={label}
              className="inline-flex items-center gap-1 font-mono text-[8.5px] tracking-[0.08em] text-console-faint uppercase"
            >
              <span
                aria-hidden="true"
                className="size-1.5"
                style={{ backgroundColor: color }}
              />
              {label}
            </span>
          ))}
        </div>
      }
      bodyClassName="flex flex-col p-0"
      className="h-full"
    >
      <div className="relative w-full flex-1">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-full w-full"
          role="img"
          aria-label={`World map with ${bubbles.length} attack origin bubbles`}
          onMouseLeave={() => setHover(null)}
        >
          <path d={spherePath} fill={COLORS.ocean} />
          <path
            d={graticulePath}
            fill="none"
            stroke={COLORS.border}
            strokeWidth={0.5}
            strokeOpacity={0.55}
          />

          {countryPaths.map((d, index) => (
            <path
              key={index}
              d={d}
              fill={COLORS.land}
              stroke={COLORS.landStroke}
              strokeWidth={0.4}
              strokeOpacity={0.85}
            />
          ))}

          <path
            d={spherePath}
            fill="none"
            stroke={COLORS.borderStrong}
            strokeWidth={0.8}
            strokeOpacity={0.9}
          />

          {bubbles.map((bubble) => (
            <g key={bubble.ip}>
              <circle
                cx={bubble.x}
                cy={bubble.y}
                r={bubble.radius + 3}
                fill={bubble.color}
                fillOpacity={0.08}
              />
              <circle
                cx={bubble.x}
                cy={bubble.y}
                r={bubble.radius}
                fill={bubble.color}
                fillOpacity={0.42}
                stroke={bubble.color}
                strokeWidth={1}
                strokeOpacity={0.95}
                tabIndex={0}
                role="button"
                aria-label={`${bubble.ip}, ${bubble.country ?? "unknown country"}, ${bubble.count} events`}
                className="cursor-pointer focus-visible:stroke-[#e9e6d9] focus-visible:outline-none"
                onMouseEnter={(event) => showHover(event, bubble)}
                onFocus={() => setHover({ bubble, x: bubble.x, y: bubble.y - 6 })}
                onBlur={() => setHover(null)}
              />
            </g>
          ))}
        </svg>

        {hover && (
          <div
            className="pointer-events-none absolute z-10 hidden w-52 -translate-x-1/2 -translate-y-[calc(100%+10px)] border border-console-border-strong bg-console-panel px-2.5 py-2 sm:block"
            style={{
              left: `${(hover.x / WIDTH) * 100}%`,
              top: `${(hover.y / HEIGHT) * 100}%`,
            }}
          >
            <div className="font-mono text-[10px] text-console-text">
              {hover.bubble.ip}
            </div>
            <div className="mt-0.5 text-[9.5px] text-console-muted">
              {hover.bubble.country ?? "Unknown"}
              {hover.bubble.city ? ` · ${hover.bubble.city}` : ""}
            </div>
            <div className="mt-0.5 truncate font-mono text-[9px] text-console-faint">
              {hover.bubble.asn ?? "ASN unknown"}
            </div>
            <div className="mt-1.5 flex items-center justify-between border-t border-console-border pt-1.5">
              <SeverityDot severity={hover.bubble.severity} />
              <span className="font-mono text-[10px] text-console-text tabular-nums">
                {compactNumber(hover.bubble.count)} evt
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-console-border px-3 py-1.5 font-mono text-[8.5px] tracking-[0.1em] text-console-faint uppercase">
        <span>Equal Earth · offline vector tiles</span>
        <span className="tabular-nums">{bubbles.length} located</span>
      </div>
    </Panel>
  );
}
