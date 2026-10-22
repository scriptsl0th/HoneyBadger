/** Types mirroring `backend/schemas.py::EventOut` and the dashboard REST contract. */

export type Service = "ssh" | "http";
export type Severity = "low" | "medium" | "high" | "critical";
export type WindowKey = "15m" | "1h" | "6h" | "24h" | "7d";

export interface LoginInfo {
  username: string | null;
  password_hash: string | null;
}

export interface GeoInfo {
  country: string | null;
  region: string | null;
  city: string | null;
  latitude: number | null;
  longitude: number | null;
  asn: string | null;
}

export interface EventOut {
  service: Service;
  source_ip: string;
  timestamp: string;
  login_info: LoginInfo | null;
  user_agent: string | null;
  http_method: string | null;
  http_path: string | null;
  http_status_code: number | null;
  command: string | null;
  payload_url: string | null;
  payload_hash: string | null;
  payload_size: number | null;
  geo_info: GeoInfo | null;
  technique_id: string | null;
  severity: Severity | null;
}

export interface Health {
  status: "ok";
  db: "ok" | "down";
  version: string;
  uptime_s: number;
}

export interface EventListResponse {
  items: EventOut[];
}

export interface EventQuery {
  limit?: number;
  service?: Service | null;
  severity?: Severity | null;
  technique?: string | null;
  since?: string | null;
}

export interface Totals {
  events: number;
  events_previous: number;
  events_per_minute: number;
  unique_sources: number;
  unique_credentials: number;
  payloads: number;
  high_or_critical: number;
}

export interface ServiceCount {
  service: Service;
  count: number;
}

export interface SeverityCount {
  severity: Severity;
  count: number;
}

export interface TechniqueCount {
  technique_id: string;
  count: number;
}

export interface CredentialCount {
  username: string;
  password_hash: string;
  count: number;
  last_seen: string;
}

export interface SourceCount {
  source_ip: string;
  country: string | null;
  city: string | null;
  latitude: number | null;
  longitude: number | null;
  asn: string | null;
  count: number;
  last_seen: string;
}

export interface PathCount {
  http_path: string;
  count: number;
}

export interface PayloadCount {
  url: string;
  hash: string | null;
  size: number | null;
  quarantined: boolean;
  first_seen: string;
}

export interface Stats {
  window: WindowKey;
  generated_at: string;
  totals: Totals;
  by_service: ServiceCount[];
  by_severity: SeverityCount[];
  by_technique: TechniqueCount[];
  top_credentials: CredentialCount[];
  top_sources: SourceCount[];
  top_paths: PathCount[];
  payloads: PayloadCount[];
}

export interface TimeseriesPoint {
  ts: string;
  total: number;
  ssh: number;
  http: number;
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export interface Timeseries {
  window: WindowKey;
  bucket_seconds: number;
  points: TimeseriesPoint[];
}
