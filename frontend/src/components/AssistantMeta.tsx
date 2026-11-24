import type { ReactNode } from "react";

import type { ChatMetadata } from "../types";

function MetaItem({
  label,
  children,
  className = "",
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className="flex min-w-0 items-baseline gap-2 border-r border-line px-3 py-2 last:border-r-0">
      <dt className="shrink-0 font-mono text-2xs uppercase tracking-[0.1em] text-faint">
        {label}
      </dt>
      <dd className={`min-w-0 truncate font-mono text-2xs ${className}`}>
        {children}
      </dd>
    </div>
  );
}

export function AssistantMeta({ metadata }: { metadata: ChatMetadata }) {
  const isCache = metadata.resolution_source === "LLM_CACHE";

  return (
    <dl className="mt-4 flex flex-wrap border-y border-line bg-surface/20 font-mono text-2xs">
      <MetaItem
        label="Source"
        className={isCache ? "text-success" : "text-accent"}
      >
        <span data-testid="meta-source">{metadata.resolution_source}</span>
      </MetaItem>
      <MetaItem label="Model" className="max-w-[220px] text-body">
        <span data-testid="meta-model">{metadata.model}</span>
      </MetaItem>
      <MetaItem label="Latency" className="text-body">
        <span data-testid="meta-latency">{metadata.latency_ms} ms</span>
      </MetaItem>
      <MetaItem label="In" className="text-body">
        <span data-testid="meta-input-tokens">{metadata.input_tokens}</span>
      </MetaItem>
      <MetaItem label="Out" className="text-body">
        <span data-testid="meta-output-tokens">{metadata.output_tokens}</span>
      </MetaItem>
      <MetaItem label="Key" className="text-body">
        {metadata.key_id ?? <span className="text-faint">CACHE</span>}
      </MetaItem>
      <MetaItem label="Fallbacks" className="text-body">
        {metadata.fallback_attempts}
      </MetaItem>
    </dl>
  );
}
