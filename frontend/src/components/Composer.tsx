import { ArrowUp, Loader2 } from "lucide-react";
import { useEffect, useRef } from "react";

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isSending: boolean;
}

export function Composer({ value, onChange, onSubmit, isSending }: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const trimmedLength = value.trim().length;
  const tooLong = trimmedLength > 4000;
  const canSend = !isSending && trimmedLength > 0 && !tooLong;

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 168)}px`;
  }, [value]);

  const submit = () => {
    if (canSend) {
      onSubmit();
    }
  };

  return (
    <div className="shrink-0 border-t border-line bg-canvas/95 pb-[max(1rem,env(safe-area-inset-bottom))] pt-4 backdrop-blur">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <div className="border border-line bg-surface/60 transition focus-within:border-line-strong">
          <div className="flex items-center justify-between border-b border-line px-3 py-2 font-mono text-2xs uppercase tracking-[0.14em]">
            <label htmlFor="chat-input" className="text-faint">
              Message
            </label>
            <span className={tooLong ? "text-danger" : "text-faint"}>
              {trimmedLength} / 4000
            </span>
          </div>

          <textarea
            ref={textareaRef}
            id="chat-input"
            data-testid="chat-input"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={(event) => {
              if (
                event.key === "Enter" &&
                !event.shiftKey &&
                !event.nativeEvent.isComposing
              ) {
                event.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder="Ask LYFTR AI anything…"
            aria-describedby="composer-hint"
            enterKeyHint="send"
            className="block max-h-[168px] min-h-[56px] w-full resize-none bg-transparent px-4 py-3 text-[15px] leading-7 text-ink placeholder:text-faint/80 focus:outline-none"
          />

          <div className="flex items-center justify-between gap-3 border-t border-line px-3 py-2">
            <span
              id="composer-hint"
              className="hidden font-mono text-2xs uppercase tracking-[0.08em] text-faint sm:inline"
            >
              Enter to send · Shift+Enter for a new line
            </span>
            <span className="font-mono text-2xs uppercase tracking-[0.08em] text-faint sm:hidden">
              {tooLong ? "Too long" : "Shift+Enter = new line"}
            </span>
            <button
              type="submit"
              data-testid="send-button"
              disabled={!canSend}
              className="inline-flex h-8 shrink-0 items-center gap-2 bg-ink px-3 font-mono text-2xs uppercase tracking-[0.12em] text-canvas transition hover:bg-white disabled:cursor-not-allowed disabled:bg-surface-strong disabled:text-faint"
              aria-label="Send message"
            >
              {isSending ? (
                <Loader2 size={13} strokeWidth={2} className="animate-spin" />
              ) : (
                <ArrowUp size={13} strokeWidth={2.25} />
              )}
              {isSending ? "Sending" : "Send"}
            </button>
          </div>
        </div>
      </form>

      <div className="mt-2 flex items-center justify-center gap-2 font-mono text-2xs uppercase tracking-[0.1em] text-faint">
        <span>Failover</span>
        <span className="text-line-strong">·</span>
        <span>Cache aware</span>
        <span className="hidden text-line-strong sm:inline">·</span>
        <span className="hidden sm:inline">SQLite memory</span>
      </div>
    </div>
  );
}
