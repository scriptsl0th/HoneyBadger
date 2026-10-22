import type { ReactNode } from "react";

interface SectionHeaderProps {
  /** Instrument index, e.g. "02". */
  index: string;
  title: string;
  hint?: ReactNode;
  actions?: ReactNode;
  id?: string;
}

/** A ruled section marker. Separates instrument clusters without card soup. */
export function SectionHeader({
  index,
  title,
  hint,
  actions,
  id,
}: SectionHeaderProps) {
  return (
    <div
      id={id}
      className="flex scroll-mt-24 items-center gap-3 pt-2 pb-0.5"
    >
      <span
        aria-hidden="true"
        className="font-mono text-[9px] leading-none font-medium text-console-accent"
      >
        {index}
      </span>
      <h2 className="label shrink-0 text-console-text">{title}</h2>
      <span aria-hidden="true" className="h-px min-w-4 flex-1 bg-console-border" />
      {hint && (
        <span className="hidden font-mono text-[9px] tracking-[0.14em] text-console-faint uppercase sm:block">
          {hint}
        </span>
      )}
      {actions}
    </div>
  );
}
