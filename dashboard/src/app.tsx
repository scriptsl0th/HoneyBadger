import { useCallback, useMemo, useState } from "react";
import { IS_MOCK } from "./api/endpoints";
import { ActivityChart } from "./components/charts/ActivityChart";
import { ServiceDonut } from "./components/charts/ServiceDonut";
import { TechniqueBars } from "./components/charts/TechniqueBars";
import { EventDetailDrawer } from "./components/feed/EventDetailDrawer";
import { EventTable } from "./components/feed/EventTable";
import { KpiRow } from "./components/layout/KpiRow";
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
    <div className="min-h-screen text-console-text">
      <TopBar
        windowKey={filters.windowKey}
        onWindowChange={filters.setWindowKey}
        connection={live.status}
        attempt={live.attempt}
        totalEvents={stats.data?.totals.events ?? null}
        generatedAt={stats.data?.generated_at ?? null}
        mock={IS_MOCK}
      />

      <main className="mx-auto max-w-[1680px] space-y-3 px-3 py-3 sm:px-5 sm:py-4 lg:px-6">
        <KpiRow
          stats={stats.data}
          windowKey={filters.windowKey}
          loading={stats.isLoading}
          error={statsError}
          onRetry={stats.refresh}
        />

        <div className="grid items-stretch gap-3 xl:grid-cols-3">
          <div className="min-w-0 xl:col-span-2">
            <ActivityChart
              timeseries={timeseries.data}
              windowKey={filters.windowKey}
              loading={timeseries.isLoading}
              error={timeseriesError}
              onRetry={timeseries.refresh}
            />
          </div>
          <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <TechniqueBars
              techniques={stats.data?.by_technique ?? null}
              loading={stats.isLoading}
              error={statsError}
              onRetry={stats.refresh}
              selectedTechnique={filters.technique}
              onSelectTechnique={filters.setTechnique}
            />
            <ServiceDonut
              services={stats.data?.by_service ?? null}
              loading={stats.isLoading}
              error={statsError}
              onRetry={stats.refresh}
            />
          </div>
        </div>

        <div className="grid min-w-0 items-stretch gap-3 xl:h-[600px] xl:grid-rows-[minmax(0,1fr)] xl:grid-cols-3 2xl:h-[640px]">
          <div className="min-h-0 min-w-0 xl:col-span-2">
            <GeoMap
              sources={stats.data?.top_sources ?? null}
              events={live.events}
              loading={stats.isLoading}
              error={statsError}
              onRetry={stats.refresh}
            />
          </div>
          <div className="min-h-0 min-w-0 xl:col-span-1">
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

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
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

        <footer className="flex flex-wrap items-center justify-between gap-2 px-1 pt-1 pb-4 text-[9.5px] tracking-wide text-console-muted/80 uppercase">
          <span>
            Credential hashes only · payloads never fetched or executed
          </span>
          <span className="font-mono normal-case">
            {stats.data
              ? `stats generated ${formatClock(stats.data.generated_at)} · auto-refresh`
              : "awaiting telemetry"}
          </span>
        </footer>
      </main>

      <EventDetailDrawer event={selectedEvent} onClose={handleCloseDrawer} />
    </div>
  );
}
