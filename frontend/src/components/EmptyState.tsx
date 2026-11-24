import { ArrowUpRight } from "lucide-react";

const CAPABILITIES = [
  {
    index: "01",
    title: "Automatic failover",
    body: "Keys rotate automatically on 429s, quota exhaustion, and 5xx failures.",
  },
  {
    index: "02",
    title: "Response caching",
    body: "LiteLLM reuses identical requests with preserved token usage.",
  },
  {
    index: "03",
    title: "Persistent memory",
    body: "Every successful turn is stored in SQLite and replayed in order.",
  },
] as const;

const EXAMPLES = [
  "Explain how automatic key failover works in one paragraph.",
  "What is the capital of France?",
  "Write a SQLite schema for conversation memory.",
] as const;

interface EmptyStateProps {
  sessionId: string;
  isSending: boolean;
  onExample: (prompt: string) => void;
}

export function EmptyState({ sessionId, isSending, onExample }: EmptyStateProps) {
  return (
    <section className="relative flex min-h-full flex-col py-6 sm:py-8">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(ellipse_at_top,rgba(107,143,255,0.09),transparent_62%)]"
        aria-hidden="true"
      />

      <div className="relative my-auto">
        <div className="flex items-center gap-3 font-mono text-2xs uppercase tracking-[0.18em] text-faint">
          <span className="h-px w-6 bg-line-strong" />
          <span>[ 01 ] Conversation engine</span>
        </div>

        <h1 className="mt-5 max-w-[720px] font-mono text-[clamp(2rem,4.8vw,3.05rem)] font-medium leading-[1.06] tracking-[-0.045em] text-ink">
          Reliable AI.
          <br />
          <span className="text-muted">Every response.</span>
        </h1>

        <p className="mt-4 max-w-[560px] text-[15px] leading-7 text-body">
          An intelligent conversational AI powered by automatic model failover,
          response caching, and persistent conversation memory.
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2 font-mono text-2xs uppercase tracking-[0.12em] text-faint">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 bg-success" />
            Session initialized
          </span>
          <span className="text-line-strong">/</span>
          <span className="break-all">{sessionId}</span>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-px border border-line bg-line sm:grid-cols-3">
          {CAPABILITIES.map((capability) => (
            <div key={capability.index} className="bg-canvas p-3.5">
              <div className="font-mono text-2xs text-accent">
                [{capability.index}]
              </div>
              <div className="mt-2 font-mono text-xs uppercase tracking-[0.1em] text-ink">
                {capability.title}
              </div>
              <p className="mt-2 text-xs leading-5 text-muted">
                {capability.body}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-6">
          <div className="font-mono text-2xs uppercase tracking-[0.18em] text-faint">
            Try a prompt
          </div>
          <div className="mt-3 grid gap-2">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => onExample(example)}
                disabled={isSending}
                className="group flex items-center justify-between gap-4 border border-line bg-surface/40 px-4 py-2.5 text-left transition hover:border-line-strong hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50"
              >
                <span className="text-sm leading-6 text-body transition group-hover:text-ink">
                  {example}
                </span>
                <ArrowUpRight
                  size={15}
                  strokeWidth={1.75}
                  className="shrink-0 text-faint transition group-hover:text-accent"
                />
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
