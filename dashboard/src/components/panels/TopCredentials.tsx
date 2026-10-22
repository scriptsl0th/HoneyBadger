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
      title="Top credentials"
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
      <ol className="divide-y divide-console-border/50">
        {(credentials ?? []).map((credential, index) => (
          <li
            key={`${credential.username}-${credential.password_hash}`}
            className="flex items-start gap-2 px-3 py-2.5 transition-colors hover:bg-white/[0.025]"
          >
            <span className="mt-0.5 w-4 shrink-0 font-mono text-[9px] text-console-muted/70 tabular-nums">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div className="min-w-0 flex-1">
              <p
                className="truncate text-[11.5px] font-medium text-console-text"
                title={credential.username}
              >
                {credential.username}
              </p>
              <div className="mt-0.5 flex min-w-0 items-center gap-1">
                <code
                  className="min-w-0 truncate font-mono text-[9.5px] text-console-muted"
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
              <div className="font-mono text-[11px] font-semibold text-console-text tabular-nums">
                {credential.count}
              </div>
              <div className="mt-0.5 text-[9px] whitespace-nowrap text-console-muted">
                {relativeTime(credential.last_seen)}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </Panel>
  );
}
