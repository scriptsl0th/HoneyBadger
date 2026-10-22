import { useCallback, useMemo, useState } from "react";
import { IS_MOCK } from "./api/endpoints";
import { ActivityChart } from "./components/charts/ActivityChart";
import { ServiceSplit } from "./components/charts/ServiceSplit";
import { TechniqueBars } from "./components/charts/TechniqueBars";
import { EventDetailDrawer } from "./components/feed/EventDetailDrawer";
import { EventTable } from "./components/feed/EventTable";
import { KpiRow } from "./components/layout/KpiRow";
import { SectionHeader } from "./components/layout/SectionHeader";
import { SideRail } from "./components/layout/SideRail";
import { TopBar } from "./components/layout/TopBar";
import { GeoMap } from "./components/map/GeoMap";
import { Payloads } from "./components/panels/Payloads";
import { TopCredentials } from "./components/panels/TopCredentials";
import { TopSources } from "./components/panels/TopSources";
import { useFilters } from "./hooks/useFilters";
import { useLiveEvents } from "./hooks/useLiveEvents";
import { useStats } from "./hooks/useStats";
import { useTimeseries } from "./hooks/useTimeseries";
import { formatClock } from "./lib/format";
import type { EventOut } from "./types";

export default function App() {
  const filters = useFilters();
  const stats = useStats(filters.windowKey);
  const timeseries = useTimeseries(filters.windowKey);
  const live = useLiveEvents({ paused: filters.paused });

  const [selectedEvent, setSelectedEvent] = useState<EventOut | null>(null);

  const handleSelectEvent = useCallback((event: EventOut) => {
    setSelectedEvent(event);
  }, []);
  const handleCloseDrawer = useCallback(() => setSelectedEvent(null), []);

  const filteredEvents = useMemo(
    () => live.events.filter(filters.matches),
    [live.events, filters.matches],
  );

  const statsError = stats.data ? null : stats.error;
  const timeseriesError = timeseries.data ? null : timeseries.error;

  return (
    <div className="min-h-screen text-console-text lg:pl-[52px]">
      <SideRail status={live.status} />

      <TopBar
        windowKey={filters.windowKey}
        onWindowChange={filters.setWindowKey}
        connection={live.status}
        attempt={live.attempt}
        totalEvents={stats.data?.totals.events ?? null}
        generatedAt={stats.data?.generated_at ?? null}
        mock={IS_MOCK}
      />

      <main className="mx-auto max-w-[1720px] px-4 pt-3 pb-6 sm:px-6">
        <div className="space-y-2.5">
          <SectionHeader
            index="01"
            title="Overview"
            hint={`Window ${filters.windowKey} · ${stats.data ? `sample ${formatClock(stats.data.generated_at)}` : "awaiting sample"}`}
          />

          <KpiRow
            stats={stats.data}
            windowKey={filters.windowKey}
            loading={stats.isLoading}
            error={statsError}
            onRetry={stats.refresh}
          />

          <SectionHeader
            index="02"
            title="Signal"
            hint="Volume · technique mix · protocol"
            id="signal"
          />

          <div className="grid gap-2.5 xl:grid-cols-3">
            <div className="min-w-0 xl:col-span-2">
              <ActivityChart
                timeseries={timeseries.data}
                windowKey={filters.windowKey}
                loading={timeseries.isLoading}
                error={timeseriesError}
                onRetry={timeseries.refresh}
              />
            </div>
            <div className="grid min-w-0 gap-2.5 sm:grid-cols-2 xl:grid-cols-1">
              <TechniqueBars
                techniques={stats.data?.by_technique ?? null}
                loading={stats.isLoading}
                error={statsError}
                onRetry={stats.refresh}
                selectedTechnique={filters.technique}
                onSelectTechnique={filters.setTechnique}
              />
              <ServiceSplit
                services={stats.data?.by_service ?? null}
                loading={stats.isLoading}
                error={statsError}
                onRetry={stats.refresh}
              />
            </div>
          </div>

          <SectionHeader
            index="03"
            title="Intelligence"
            hint="Geography · live intercepts"
            id="intel"
          />

          <div className="grid min-w-0 items-stretch gap-2.5 xl:h-[608px] xl:grid-cols-12">
            <div className="min-h-0 min-w-0 xl:col-span-7">
              <GeoMap
                sources={stats.data?.top_sources ?? null}
                events={live.events}
                loading={stats.isLoading}
                error={statsError}
                onRetry={stats.refresh}
              />
            </div>
            <div className="min-h-0 min-w-0 xl:col-span-5">
              <EventTable
                events={filteredEvents}
                loading={live.isLoading}
                error={live.error}
                onRetry={live.refresh}
                paused={filters.paused}
                onTogglePause={() => filters.setPaused(!filters.paused)}
                pendingCount={live.pendingCount}
                service={filters.service}
                onServiceChange={filters.setService}
                severity={filters.severity}
                onSeverityChange={filters.setSeverity}
                technique={filters.technique}
                onTechniqueChange={filters.setTechnique}
                activeFilterCount={filters.activeFilterCount}
                onResetFilters={filters.resetFilters}
                onSelectEvent={handleSelectEvent}
              />
            </div>
          </div>

          <SectionHeader
            index="04"
            title="Records"
            hint="Aggregates from the selected window"
            id="records"
          />

          <div className="grid gap-2.5 md:grid-cols-2 xl:grid-cols-3">
            <TopCredentials
              credentials={stats.data?.top_credentials ?? null}
              loading={stats.isLoading}
              error={statsError}
              onRetry={stats.refresh}
            />
            <TopSources
              sources={stats.data?.top_sources ?? null}
              loading={stats.isLoading}
              error={statsError}
              onRetry={stats.refresh}
            />
            <div className="md:col-span-2 xl:col-span-1">
              <Payloads
                payloads={stats.data?.payloads ?? null}
                loading={stats.isLoading}
                error={statsError}
                onRetry={stats.refresh}
              />
            </div>
          </div>

          <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-console-border pt-3 pb-1 font-mono text-[8.5px] tracking-[0.1em] text-console-faint uppercase">
            <span>Read-only console · hashes only · payloads never fetched</span>
            <span className="normal-case">
              {stats.data
                ? `stats generated ${formatClock(stats.data.generated_at)} · auto-refresh`
                : "awaiting telemetry"}
            </span>
          </footer>
        </div>
      </main>

      <EventDetailDrawer event={selectedEvent} onClose={handleCloseDrawer} />
    </div>
  );
}
