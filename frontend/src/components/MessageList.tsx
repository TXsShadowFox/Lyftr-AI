import { useEffect, useState } from "react";
import type { UiMessage } from "../types";
import { AssistantMeta } from "./AssistantMeta";

function UserMessage({ message }: { message: Extract<UiMessage, { role: "user" }> }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[88%] border border-line bg-surface px-4 py-3 sm:max-w-[74%]">
        <div className="mb-2 flex items-center justify-end gap-2 font-mono text-2xs uppercase tracking-[0.12em] text-faint">
          <span>You</span>
          <span className="h-1 w-1 bg-line-strong" />
          <span>{message.content.length} chars</span>
        </div>
        <p className="whitespace-pre-wrap break-words text-[15px] leading-7 text-ink">
          {message.content}
        </p>
      </div>
    </div>
  );
}

function AssistantMessage({
  message,
}: {
  message: Extract<UiMessage, { role: "assistant" }>;
}) {
  const isCache = message.metadata.resolution_source === "LLM_CACHE";

  return (
    <article
      data-testid="assistant-message"
      className={`relative animate-fade-up border-l-2 pl-4 sm:pl-5 ${
        isCache ? "border-success/70" : "border-accent/70"
      }`}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-mono text-2xs uppercase tracking-[0.16em] text-ink">
          LYFTR AI
        </span>
        <span className="h-1 w-1 bg-line-strong" />
        <span className="font-mono text-2xs uppercase tracking-[0.12em] text-faint">
          Assistant
        </span>
        <span
          className={`ml-auto font-mono text-2xs uppercase tracking-[0.12em] ${
            isCache ? "text-success" : "text-accent"
          }`}
        >
          {isCache ? "Cache hit" : "Live"}
        </span>
      </div>

      <div className="mt-3 whitespace-pre-wrap break-words text-[15px] leading-7 text-[#e8e8e8]">
        {message.content}
      </div>

      <AssistantMeta metadata={message.metadata} />
    </article>
  );
}

function ThinkingMessage() {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - started) / 100) / 10);
    }, 100);
    return () => clearInterval(interval);
  }, []);

  return (
    <article
      className="relative animate-fade-up border-l-2 border-line-strong pl-4 sm:pl-5"
      aria-live="polite"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-mono text-2xs uppercase tracking-[0.16em] text-ink">
          LYFTR AI
        </span>
        <span className="h-1 w-1 bg-line-strong" />
        <span className="font-mono text-2xs uppercase tracking-[0.12em] text-faint">
          Generating · {elapsed.toFixed(1)}s
        </span>
      </div>
      <div className="mt-4 flex items-center gap-1.5" aria-hidden="true">
        <span className="h-1.5 w-1.5 animate-blink bg-accent" />
        <span className="h-1.5 w-1.5 animate-blink bg-accent [animation-delay:160ms]" />
        <span className="h-1.5 w-1.5 animate-blink bg-accent [animation-delay:320ms]" />
      </div>
      <span className="sr-only">The assistant is generating a response.</span>
    </article>
  );
}

export function MessageList({
  messages,
  isSending,
}: {
  messages: UiMessage[];
  isSending: boolean;
}) {
  return (
    <div className="space-y-8 py-8">
      {messages.map((message) =>
        message.role === "user" ? (
          <UserMessage key={message.id} message={message} />
        ) : (
          <AssistantMessage key={message.id} message={message} />
        ),
      )}
      {isSending ? <ThinkingMessage /> : null}
    </div>
  );
}
