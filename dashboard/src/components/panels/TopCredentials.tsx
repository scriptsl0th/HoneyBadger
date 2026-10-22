import type { CredentialCount } from "../../types";
import { relativeTime, shortHash } from "../../lib/format";
import { Panel } from "../layout/Panel";
import { CopyButton } from "../ui/CopyButton";
import { EmptyState } from "../ui/EmptyState";

interface TopCredentialsProps {
  credentials: CredentialCount[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function TopCredentials({
  credentials,
  loading,
  error,
  onRetry,
}: TopCredentialsProps) {
  return (
    <Panel
      index="04.1"
      title="Credential attempts"
      subtitle="Username + SHA-256 password hash"
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={!loading && !error && (credentials?.length ?? 0) === 0}
      emptyState={
        <EmptyState
          title="No credentials captured"
          message="SSH and HTTP login attempts will surface here as username/hash pairs."
        />
      }
      bodyClassName="p-0"
      className="h-full"
    >
      <ol className="scrollbar-thin max-h-[352px] divide-y divide-console-border/55 overflow-y-auto">
        {(credentials ?? []).map((credential, index) => (
          <li
            key={`${credential.username}-${credential.password_hash}`}
            className="flex items-start gap-2 px-3 py-2 transition-colors hover:bg-white/[0.025]"
          >
            <span className="mt-0.5 w-5 shrink-0 font-mono text-[8.5px] text-console-faint tabular-nums">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div className="min-w-0 flex-1">
              <p
                className="truncate text-[11px] leading-tight font-medium text-console-text"
                title={credential.username}
              >
                {credential.username}
              </p>
              <div className="mt-1 flex min-w-0 items-center gap-1">
                <code
                  className="min-w-0 truncate font-mono text-[9px] text-console-faint"
                  title={credential.password_hash}
                >
                  {shortHash(credential.password_hash, 14, 4)}
                </code>
                <CopyButton
                  value={credential.password_hash}
                  label="Hash"
                  compact
                  className="shrink-0"
                />
              </div>
            </div>
            <div className="shrink-0 text-right">
              <div className="font-mono text-[11px] leading-none font-medium text-console-text tabular-nums">
                {credential.count}
              </div>
              <div className="mt-1 font-mono text-[8.5px] whitespace-nowrap text-console-faint">
                {relativeTime(credential.last_seen)}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </Panel>
  );
}
