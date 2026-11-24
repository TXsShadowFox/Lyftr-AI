import type { HealthState } from "../hooks/useHealth";

const LABELS: Record<HealthState["status"], string> = {
  loading: "CHECKING",
  ok: "ONLINE",
  degraded: "DEGRADED",
  offline: "OFFLINE",
};

const DOT_CLASSES: Record<HealthState["status"], string> = {
  loading: "bg-faint animate-dot-pulse",
  ok: "bg-success",
  degraded: "bg-warning",
  offline: "bg-danger",
};

const TEXT_CLASSES: Record<HealthState["status"], string> = {
  loading: "text-faint",
  ok: "text-success",
  degraded: "text-warning",
  offline: "text-danger",
};

export function StatusChip({
  state,
  compact = false,
}: {
  state: HealthState;
  compact?: boolean;
}) {
  return (
    <span
      className="inline-flex items-center gap-2 font-mono text-2xs uppercase tracking-[0.14em]"
      title={
        state.status === "degraded" || state.status === "offline"
          ? state.detail
          : "API status"
      }
    >
      <span className={`h-1.5 w-1.5 shrink-0 ${DOT_CLASSES[state.status]}`} />
      <span className={TEXT_CLASSES[state.status]}>{LABELS[state.status]}</span>
      {!compact && state.status === "ok" ? (
        <span className="hidden text-faint sm:inline">
          / {state.data.keys_configured} KEYS
        </span>
      ) : null}
    </span>
  );
}
