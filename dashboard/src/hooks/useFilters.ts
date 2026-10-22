import { useCallback, useState } from "react";
import type { EventOut, Service, Severity, WindowKey } from "../types";

export type ServiceFilter = Service | "all";
export type SeverityFilter = Severity | "all";

export interface Filters {
  windowKey: WindowKey;
  setWindowKey: (value: WindowKey) => void;
  service: ServiceFilter;
  setService: (value: ServiceFilter) => void;
  severity: SeverityFilter;
  setSeverity: (value: SeverityFilter) => void;
  technique: string;
  setTechnique: (value: string) => void;
  paused: boolean;
  setPaused: (value: boolean) => void;
  resetFilters: () => void;
  matches: (event: EventOut) => boolean;
  activeFilterCount: number;
}

export function useFilters(): Filters {
  const [windowKey, setWindowKey] = useState<WindowKey>("1h");
  const [service, setService] = useState<ServiceFilter>("all");
  const [severity, setSeverity] = useState<SeverityFilter>("all");
  const [technique, setTechnique] = useState("all");
  const [paused, setPaused] = useState(false);

  const matches = useCallback(
    (event: EventOut) => {
      if (service !== "all" && event.service !== service) return false;
      if (severity !== "all" && event.severity !== severity) return false;
      if (technique !== "all" && event.technique_id !== technique) return false;
      return true;
    },
    [service, severity, technique],
  );

  const resetFilters = useCallback(() => {
    setService("all");
    setSeverity("all");
    setTechnique("all");
  }, []);

  const activeFilterCount =
    (service === "all" ? 0 : 1) +
    (severity === "all" ? 0 : 1) +
    (technique === "all" ? 0 : 1);

  return {
    windowKey,
    setWindowKey,
    service,
    setService,
    severity,
    setSeverity,
    technique,
    setTechnique,
    paused,
    setPaused,
    resetFilters,
    matches,
    activeFilterCount,
  };
}
