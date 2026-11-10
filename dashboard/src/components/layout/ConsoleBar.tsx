import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import type { Filters, ServiceFilter, SeverityFilter } from "../../hooks/useFilters";
import type { WindowKey } from "../../types";
import { TECHNIQUE_IDS } from "../../lib/techniques";

const WINDOWS: readonly WindowKey[] = ["15m", "1h", "6h", "24h", "7d"];
const SECTIONS = ["overview", "signal", "intel", "records"] as const;
const SERVICES: readonly ServiceFilter[] = ["ssh", "http", "all"];
const SEVERITIES: readonly SeverityFilter[] = ["low", "medium", "high", "critical", "all"];

interface Message {
  tone: "ok" | "error";
  text: string;
}

/** A command line for the console. Small grammar, real actions. */
export function ConsoleBar({ filters }: { filters: Filters }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState("");
  const [message, setMessage] = useState<Message | null>(null);
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      const typing =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.isContentEditable;
      const commandKey =
        event.key === "/" ||
        ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k");

      if (commandKey && !typing && !event.altKey) {
        event.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const ok = (text: string) => setMessage({ tone: "ok", text });
  const fail = (text: string) => setMessage({ tone: "error", text });

  const run = (raw: string) => {
    const command = raw.trim();
    if (!command) return;

    setHistory((previous) => [...previous.slice(-19), command]);
    setHistoryIndex(-1);
    setValue("");

    const [name, ...rest] = command.split(/\s+/);
    const argument = rest.join(" ").toLowerCase();

    switch (name.toLowerCase()) {
      case "help":
        ok(
          "window [15m|1h|6h|24h|7d] · service [ssh|http|all] · severity [low|medium|high|critical|all] · technique [T1110…|all] · status · pause|resume · reset · goto [section]",
        );
        return;

      case "window":
        if (WINDOWS.includes(argument as WindowKey)) {
          filters.setWindowKey(argument as WindowKey);
          ok(`window → ${argument}`);
        } else {
          fail(`window must be one of ${WINDOWS.join(", ")}`);
        }
        return;

      case "service":
        if (SERVICES.includes(argument as ServiceFilter)) {
          filters.setService(argument as ServiceFilter);
          ok(`service → ${argument}`);
        } else {
          fail("service must be ssh, http, or all");
        }
        return;

      case "severity":
        if (SEVERITIES.includes(argument as SeverityFilter)) {
          filters.setSeverity(argument as SeverityFilter);
          ok(`severity → ${argument}`);
        } else {
          fail("severity must be low, medium, high, critical, or all");
        }
        return;

      case "technique": {
        const technique = argument.toUpperCase();
        if (technique === "ALL" || TECHNIQUE_IDS.some((id) => id === technique)) {
          filters.setTechnique(technique === "ALL" ? "all" : technique);
          ok(`technique → ${technique}`);
        } else {
          fail("technique must be an ATT&CK id such as T1110, or all");
        }
        return;
      }

      case "pause":
        filters.setPaused(true);
        ok("stream paused");
        return;

      case "resume":
        filters.setPaused(false);
        ok("stream resumed");
        return;

      case "reset":
        filters.resetFilters();
        ok("filters cleared");
        return;

      case "status":
        ok(
          `win ${filters.windowKey} · svc ${filters.service} · sev ${filters.severity} · tech ${filters.technique}${filters.paused ? " · paused" : ""}`,
        );
        return;

      case "goto":
        if (SECTIONS.includes(argument as (typeof SECTIONS)[number])) {
          document.getElementById(argument)?.scrollIntoView({ block: "start" });
          ok(`goto → ${argument}`);
        } else {
          fail(`goto must be one of ${SECTIONS.join(", ")}`);
        }
        return;

      case "clear":
        setMessage(null);
        return;

      default:
        fail(`unknown command "${name}" — type help`);
    }
  };

  const onInputKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      run(value);
      return;
    }

    if (event.key === "Escape") {
      inputRef.current?.blur();
      return;
    }

    if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
    event.preventDefault();

    if (history.length === 0) return;

    if (event.key === "ArrowUp") {
      const next = historyIndex === -1 ? history.length - 1 : Math.max(0, historyIndex - 1);
      setHistoryIndex(next);
      setValue(history[next]);
      return;
    }

    if (historyIndex === -1) return;
    const next = historyIndex + 1;
    if (next >= history.length) {
      setHistoryIndex(-1);
      setValue("");
    } else {
      setHistoryIndex(next);
      setValue(history[next]);
    }
  };

  return (
    <div className="border-b border-console-border bg-console-panel">
      <div className="mx-auto flex min-h-9 max-w-[1720px] flex-wrap items-center gap-x-2 gap-y-0 px-4 py-1.5 sm:gap-x-3 sm:px-6">
        <span
          aria-hidden="true"
          className="shrink-0 font-mono text-[10px] leading-none text-console-accent"
        >
          hb@hb-01:/ops$
        </span>

        <input
          ref={inputRef}
          type="text"
          name="console-command"
          aria-label="Console command"
          aria-keyshortcuts="Control+K /"
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setHistoryIndex(-1);
          }}
          onKeyDown={onInputKeyDown}
          placeholder={'try "severity high", "window 24h", "pause" — or help'}
          className="min-w-0 flex-1 bg-transparent py-1.5 font-mono text-[11px] leading-none text-console-text caret-console-accent placeholder:text-console-faint"
        />

        <span
          aria-live="polite"
          title={message?.text}
          className={`order-last w-full truncate font-mono text-[9px] leading-tight md:order-none md:w-auto ${
            message
              ? message.tone === "error"
                ? "text-[#ec8a86] md:max-w-[44%]"
                : "text-console-muted md:max-w-[44%]"
              : "md:max-w-0"
          }`}
        >
          {message ? `${message.tone === "error" ? "!" : ">"} ${message.text}` : ""}
        </span>

        <kbd className="hidden shrink-0 border border-console-border px-1 py-0.5 font-mono text-[8px] leading-none tracking-[0.08em] text-console-faint uppercase sm:block">
          enter
        </kbd>
      </div>
    </div>
  );
}
