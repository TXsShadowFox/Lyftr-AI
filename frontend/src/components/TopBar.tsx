import { PanelLeftClose, PanelLeftOpen, Plus } from "lucide-react";

import type { HealthState } from "../hooks/useHealth";
import { shortSessionId } from "../lib/session";
import { StatusChip } from "./StatusChip";

interface TopBarProps {
  health: HealthState;
  sessionId: string;
  isSending: boolean;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  onNewSession: () => void;
}

export function TopBar({
  health,
  sessionId,
  isSending,
  isSidebarOpen,
  onToggleSidebar,
  onNewSession,
}: TopBarProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-line bg-canvas/90 px-4 backdrop-blur lg:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="inline-flex h-8 w-8 items-center justify-center border border-line text-body transition hover:border-line-strong hover:text-ink"
          aria-label={isSidebarOpen ? "Collapse sidebar" : "Open navigation"}
          title={isSidebarOpen ? "Hide sidebar" : "Show sidebar"}
          aria-controls="app-sidebar"
        >
          {isSidebarOpen ? (
            <PanelLeftClose size={15} strokeWidth={1.75} />
          ) : (
            <PanelLeftOpen size={15} strokeWidth={1.75} />
          )}
        </button>
        <div className="flex min-w-0 items-center gap-2 font-mono text-2xs uppercase tracking-[0.14em]">
          <span className="whitespace-nowrap text-muted">LYFTR AI</span>
          <span className="hidden text-line-strong sm:inline">/</span>
          <span className="hidden truncate text-ink sm:inline">Conversation</span>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3 sm:gap-5">
        <StatusChip state={health} />
        <span className="hidden font-mono text-2xs uppercase tracking-[0.12em] text-faint md:inline">
          Session {shortSessionId(sessionId)}
        </span>
        <button
          type="button"
          onClick={onNewSession}
          disabled={isSending}
          className="inline-flex h-8 items-center gap-2 border border-line px-2.5 font-mono text-2xs uppercase tracking-[0.12em] text-body transition hover:border-line-strong hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Start a new session"
        >
          <Plus size={13} strokeWidth={2} />
          <span className="hidden sm:inline">New</span>
        </button>
      </div>
    </header>
  );
}
