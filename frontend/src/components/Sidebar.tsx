import {
  ArrowUpRight,
  Check,
  Copy,
  Plus,
  RefreshCw,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";

import type { HealthState } from "../hooks/useHealth";
import { API_BASE_URL } from "../lib/api";
import type { ChatMetadata, UiMessage } from "../types";
import { BrandMark } from "./BrandMark";
import { StatusChip } from "./StatusChip";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  health: HealthState;
  isRefreshingHealth: boolean;
  onRefreshHealth: () => void;
  sessionId: string;
  messages: UiMessage[];
  lastMetadata: ChatMetadata | null;
  systemPrompt: string;
  onSystemPromptChange: (value: string) => void;
  onNewSession: () => void;
  isSending: boolean;
}

export function Sidebar({
  open,
  onClose,
  health,
  isRefreshingHealth,
  onRefreshHealth,
  sessionId,
  messages,
  lastMetadata,
  systemPrompt,
  onSystemPromptChange,
  onNewSession,
  isSending,
}: SidebarProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) {
      return;
    }
    const timer = window.setTimeout(() => setCopied(false), 1600);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const copySessionId = async () => {
    try {
      await navigator.clipboard.writeText(sessionId);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const keys =
    health.status === "ok"
      ? health.data.keys_configured
      : health.status === "degraded"
        ? health.keysConfigured
        : undefined;
  const cache =
    health.status === "ok"
      ? health.data.cache_enabled
      : health.status === "degraded"
        ? health.cacheEnabled
        : undefined;

  return (
    <aside
      id="app-sidebar"
      aria-label="Session navigation"
      className={`fixed inset-y-0 left-0 z-40 flex w-[264px] shrink-0 flex-col border-r border-line bg-panel transition-transform duration-200 ease-out lg:static lg:z-auto lg:translate-x-0 ${
        open ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      <div className="flex h-full min-h-0 flex-col overflow-y-auto">
        <div className="flex items-center justify-between border-b border-line px-5 py-5">
          <div className="flex items-center gap-3">
            <BrandMark />
            <div>
              <div className="font-mono text-sm font-medium tracking-[0.16em] text-ink">
                LYFTR AI
              </div>
              <div className="mt-0.5 text-2xs text-muted">
                Reliable AI. Every Response.
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-8 w-8 items-center justify-center border border-line text-body transition hover:border-line-strong hover:text-ink lg:hidden"
            aria-label="Close navigation"
          >
            <X size={15} strokeWidth={1.75} />
          </button>
        </div>

        <div className="px-5 py-5">
          <div className="mb-3 font-mono text-2xs uppercase tracking-[0.18em] text-faint">
            Navigation
          </div>
          <nav className="space-y-px" aria-label="Primary">
            <div className="flex items-center gap-3 border-l-2 border-accent bg-surface/70 py-2.5 pl-3 pr-2">
              <span className="font-mono text-2xs text-accent">01</span>
              <span className="font-mono text-xs uppercase tracking-[0.1em] text-ink">
                Conversation
              </span>
            </div>
            <button
              type="button"
              onClick={onNewSession}
              disabled={isSending}
              className="flex w-full items-center gap-3 border-l-2 border-transparent py-2.5 pl-3 pr-2 text-left transition hover:border-line-strong hover:bg-surface/40 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <span className="font-mono text-2xs text-faint">02</span>
              <span className="font-mono text-xs uppercase tracking-[0.1em] text-body">
                New session
              </span>
              <Plus size={13} className="ml-auto text-faint" strokeWidth={1.75} />
            </button>
            <a
              href={`${API_BASE_URL}/docs`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-3 border-l-2 border-transparent py-2.5 pl-3 pr-2 transition hover:border-line-strong hover:bg-surface/40"
            >
              <span className="font-mono text-2xs text-faint">03</span>
              <span className="font-mono text-xs uppercase tracking-[0.1em] text-body">
                API reference
              </span>
              <ArrowUpRight
                size={13}
                className="ml-auto text-faint"
                strokeWidth={1.75}
              />
            </a>
          </nav>
        </div>

        <div className="border-t border-line px-5 py-5">
          <div className="mb-3 font-mono text-2xs uppercase tracking-[0.18em] text-faint">
            Session
          </div>
          <div className="space-y-4">
            <div>
              <div className="font-mono text-2xs uppercase tracking-[0.12em] text-faint">
                Identifier
              </div>
              <div className="mt-1.5 flex items-start gap-2">
                <span className="min-w-0 break-all font-mono text-xs leading-5 text-body">
                  {sessionId}
                </span>
                <button
                  type="button"
                  onClick={() => void copySessionId()}
                  className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center border border-line text-faint transition hover:border-line-strong hover:text-ink"
                  aria-label="Copy session identifier"
                >
                  {copied ? (
                    <Check size={11} strokeWidth={2} />
                  ) : (
                    <Copy size={11} strokeWidth={1.75} />
                  )}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="border border-line px-2.5 py-2">
                <div className="font-mono text-2xs uppercase tracking-[0.1em] text-faint">
                  Messages
                </div>
                <div className="mt-0.5 font-mono text-xs text-ink">
                  {messages.length}
                </div>
              </div>
              <div className="border border-line px-2.5 py-2">
                <div className="font-mono text-2xs uppercase tracking-[0.1em] text-faint">
                  Source
                </div>
                <div
                  className={`mt-0.5 font-mono text-2xs ${
                    lastMetadata?.resolution_source === "LLM_CACHE"
                      ? "text-success"
                      : lastMetadata
                        ? "text-accent"
                        : "text-faint"
                  }`}
                  title={lastMetadata?.resolution_source}
                >
                  {lastMetadata
                    ? lastMetadata.resolution_source === "LLM_CACHE"
                      ? "CACHE"
                      : "LIVE"
                    : "—"}
                </div>
              </div>
            </div>

            <div>
              <div className="font-mono text-2xs uppercase tracking-[0.12em] text-faint">
                Model
              </div>
              <div className="mt-1 break-all font-mono text-2xs leading-4 text-body">
                {lastMetadata?.model ?? "Awaiting first reply"}
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-line px-5 py-5">
          <div className="mb-2 flex items-center justify-between">
            <label
              htmlFor="system-prompt"
              className="font-mono text-2xs uppercase tracking-[0.18em] text-faint"
            >
              System prompt
            </label>
            <span
              className={`font-mono text-2xs uppercase tracking-[0.1em] ${
                systemPrompt.trim() ? "text-accent" : "text-faint"
              }`}
            >
              {systemPrompt.trim() ? "Active" : "Optional"}
            </span>
          </div>
          <textarea
            id="system-prompt"
            data-testid="system-prompt-input"
            value={systemPrompt}
            onChange={(event) => onSystemPromptChange(event.target.value)}
            rows={4}
            maxLength={8000}
            placeholder="Set a tone, role, or constraint for this session…"
            className="block w-full resize-y border border-line bg-canvas px-3 py-2.5 font-mono text-xs leading-5 text-body placeholder:text-faint/70 focus:border-line-strong focus:outline-none"
          />
          <div className="mt-2 flex items-center justify-between font-mono text-2xs text-faint">
            <span>Applied to this session</span>
            <span>{systemPrompt.length} / 8000</span>
          </div>
        </div>

        <div className="mt-auto border-t border-line px-5 py-4">
          <div className="flex items-center justify-between">
            <StatusChip state={health} compact />
            <button
              type="button"
              onClick={onRefreshHealth}
              className="inline-flex h-6 w-6 items-center justify-center text-faint transition hover:text-ink"
              aria-label="Refresh API status"
            >
              <RefreshCw
                size={12}
                strokeWidth={1.75}
                className={isRefreshingHealth ? "animate-spin" : ""}
              />
            </button>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2">
            <div className="border border-line px-2.5 py-2">
              <div className="font-mono text-2xs uppercase tracking-[0.1em] text-faint">
                Keys
              </div>
              <div className="mt-0.5 font-mono text-xs text-body">
                {keys ?? "—"}
              </div>
            </div>
            <div className="border border-line px-2.5 py-2">
              <div className="font-mono text-2xs uppercase tracking-[0.1em] text-faint">
                Cache
              </div>
              <div
                className={`mt-0.5 font-mono text-xs ${
                  cache === false ? "text-warning" : "text-body"
                }`}
              >
                {cache === undefined ? "—" : cache ? "ON" : "OFF"}
              </div>
            </div>
          </div>

          {(health.status === "degraded" || health.status === "offline") &&
          health.detail ? (
            <p className="mt-2 text-2xs leading-4 text-warning/90">
              {health.detail}
            </p>
          ) : null}

          <div className="mt-4 flex items-center justify-between gap-2 border-t border-line pt-3 font-mono text-[10px] uppercase tracking-[0.05em] text-faint">
            <span className="whitespace-nowrap">LYFTR AI v1.0</span>
            <span className="whitespace-nowrap">React · FastAPI</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
