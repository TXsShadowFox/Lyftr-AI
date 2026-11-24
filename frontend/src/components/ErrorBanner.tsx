import { AlertTriangle, RotateCcw, X } from "lucide-react";

export function ErrorBanner({
  message,
  onRetry,
  onDismiss,
}: {
  message: string;
  onRetry?: () => void;
  onDismiss: () => void;
}) {
  return (
    <div
      role="alert"
      className="mt-4 flex items-start gap-3 border border-danger/35 bg-danger/5 px-4 py-3"
    >
      <AlertTriangle
        size={15}
        strokeWidth={1.75}
        className="mt-0.5 shrink-0 text-danger"
      />
      <div className="min-w-0 flex-1">
        <div className="font-mono text-2xs uppercase tracking-[0.14em] text-danger">
          Request failed
        </div>
        <p className="mt-1 break-words text-sm leading-6 text-body">{message}</p>
      </div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex h-7 shrink-0 items-center gap-1.5 border border-line px-2 font-mono text-2xs uppercase tracking-[0.1em] text-body transition hover:border-line-strong hover:text-ink"
        >
          <RotateCcw size={11} strokeWidth={1.75} />
          Retry
        </button>
      ) : null}
      <button
        type="button"
        onClick={onDismiss}
        className="inline-flex h-7 w-7 shrink-0 items-center justify-center text-faint transition hover:text-ink"
        aria-label="Dismiss error"
      >
        <X size={14} strokeWidth={1.75} />
      </button>
    </div>
  );
}
