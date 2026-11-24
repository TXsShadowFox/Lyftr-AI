import { useEffect, useRef, useState } from "react";

import { Composer } from "./components/Composer";
import { EmptyState } from "./components/EmptyState";
import { ErrorBanner } from "./components/ErrorBanner";
import { MessageList } from "./components/MessageList";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { useChat } from "./hooks/useChat";
import { useHealth } from "./hooks/useHealth";

export default function App() {
  const chat = useChat();
  const health = useHealth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(() => {
    try {
      return localStorage.getItem("lyftr_sidebar_collapsed") === "true";
    } catch {
      return false;
    }
  });
  const [isDesktop, setIsDesktop] = useState(
    typeof window !== "undefined" ? window.innerWidth >= 1024 : true,
  );
  const [systemPrompt, setSystemPrompt] = useState("");
  const [promptTouched, setPromptTouched] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mql = window.matchMedia("(min-width: 1024px)");
    const onChange = () => setIsDesktop(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSidebarOpen(false);
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
        event.preventDefault();
        if (window.innerWidth >= 1024) {
          handleToggleDesktop();
        } else {
          setSidebarOpen((prev) => !prev);
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const handleToggleDesktop = () => {
    setDesktopCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("lyftr_sidebar_collapsed", String(next));
      } catch {}
      return next;
    });
  };

  const handleToggleSidebar = () => {
    if (isDesktop) {
      handleToggleDesktop();
    } else {
      setSidebarOpen((prev) => !prev);
    }
  };

  const handleCloseSidebar = () => {
    if (isDesktop) {
      setDesktopCollapsed(true);
      try {
        localStorage.setItem("lyftr_sidebar_collapsed", "true");
      } catch {}
    } else {
      setSidebarOpen(false);
    }
  };

  const isSidebarOpen = isDesktop ? !desktopCollapsed : sidebarOpen;

  useEffect(() => {
    if (!sidebarOpen) {
      return;
    }
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [sidebarOpen]);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) {
      return;
    }
    if (chat.messages.length === 0 && !chat.isSending) {
      // The empty state is taller than the viewport on small screens. Keep it
      // anchored at the top instead of auto-scrolling to the composer.
      node.scrollTo({ top: 0, behavior: "auto" });
      return;
    }
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    node.scrollTo({
      top: node.scrollHeight,
      behavior: reduced ? "auto" : "smooth",
    });
  }, [chat.messages, chat.isSending, chat.error]);

  const handleSystemPromptChange = (value: string) => {
    setSystemPrompt(value);
    setPromptTouched(true);
  };

  const handleNewSession = () => {
    chat.newSession();
    // A new conversation starts with a fresh session-level prompt. Otherwise
    // the previous session's prompt would silently carry over.
    setSystemPrompt("");
    setPromptTouched(false);
    setSidebarOpen(false);
  };

  const sendOptions = { systemPrompt, promptTouched };

  return (
    <div className="flex h-dvh overflow-hidden bg-canvas">
      <Sidebar
        open={sidebarOpen}
        desktopCollapsed={desktopCollapsed}
        onClose={handleCloseSidebar}
        health={health.state}
        isRefreshingHealth={health.isRefreshing}
        onRefreshHealth={health.refresh}
        sessionId={chat.sessionId}
        messages={chat.messages}
        lastMetadata={chat.lastMetadata}
        systemPrompt={systemPrompt}
        onSystemPromptChange={handleSystemPromptChange}
        onNewSession={handleNewSession}
        isSending={chat.isSending}
      />

      {sidebarOpen ? (
        <button
          type="button"
          aria-label="Close navigation overlay"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-[1px] lg:hidden"
        />
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          health={health.state}
          sessionId={chat.sessionId}
          isSending={chat.isSending}
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={handleToggleSidebar}
          onNewSession={handleNewSession}
        />

        <main className="flex min-h-0 flex-1 flex-col">
          <div className="mx-auto flex min-h-0 w-full max-w-[860px] flex-1 flex-col px-4 sm:px-6">
            {chat.error ? (
              <ErrorBanner
                message={chat.error}
                onRetry={
                  chat.canRetry
                    ? () => chat.retry(sendOptions)
                    : undefined
                }
                onDismiss={chat.dismissError}
              />
            ) : null}

            <div
              ref={scrollRef}
              className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden"
              aria-label="Conversation"
            >
              {chat.messages.length === 0 && !chat.isSending ? (
                <EmptyState
                  sessionId={chat.sessionId}
                  isSending={chat.isSending}
                  onExample={(prompt) => void chat.send(prompt, sendOptions)}
                />
              ) : (
                <MessageList
                  messages={chat.messages}
                  isSending={chat.isSending}
                />
              )}
            </div>

            <Composer
              value={chat.input}
              onChange={chat.setInput}
              onSubmit={() => void chat.send(chat.input, sendOptions)}
              isSending={chat.isSending}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
