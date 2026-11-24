import { useCallback, useRef, useState } from "react";

import { describeApiError, sendChat } from "../lib/api";
import { createSessionId } from "../lib/session";
import type { ChatMetadata, UiMessage } from "../types";

export interface SendOptions {
  systemPrompt: string;
  promptTouched: boolean;
}

function localId(prefix: string): string {
  const random =
    globalThis.crypto?.randomUUID?.() ??
    Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
  return `${prefix}-${random}`;
}

export function useChat() {
  const [sessionId, setSessionId] = useState(createSessionId);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryText, setRetryText] = useState<string | null>(null);
  const [lastMetadata, setLastMetadata] = useState<ChatMetadata | null>(null);
  const sendingRef = useRef(false);

  const send = useCallback(
    async (raw: string, options: SendOptions) => {
      if (sendingRef.current) {
        return;
      }

      const message = raw.trim();
      if (!message) {
        return;
      }
      if (message.length > 4000) {
        setError(
          "Messages are limited to 4,000 characters. Shorten your message and try again.",
        );
        return;
      }

      sendingRef.current = true;
      setIsSending(true);
      setError(null);
      setRetryText(null);
      setInput("");

      const optimistic: UiMessage = {
        id: localId("user"),
        role: "user",
        content: message,
      };
      setMessages((current) => [...current, optimistic]);

      try {
        const response = await sendChat({
          session_id: sessionId,
          message,
          ...(options.promptTouched
            ? { system_prompt: options.systemPrompt }
            : {}),
        });

        const assistant: UiMessage = {
          id: localId("assistant"),
          role: "assistant",
          content: response.reply,
          metadata: response.metadata,
        };
        setMessages((current) => [...current, assistant]);
        setLastMetadata(response.metadata);
      } catch (requestError) {
        // Failed exchanges are never persisted by the API, so remove the
        // optimistic turn and offer an explicit retry instead of pretending
        // it is part of the conversation.
        setMessages((current) =>
          current.filter((item) => item.id !== optimistic.id),
        );
        setError(describeApiError(requestError));
        setRetryText(message);
      } finally {
        sendingRef.current = false;
        setIsSending(false);
      }
    },
    [sessionId],
  );

  const retry = useCallback(
    (options: SendOptions) => {
      if (!retryText) {
        return;
      }
      void send(retryText, options);
    },
    [retryText, send],
  );

  const newSession = useCallback(() => {
    if (sendingRef.current) {
      return;
    }
    setSessionId(createSessionId());
    setMessages([]);
    setInput("");
    setError(null);
    setRetryText(null);
    setLastMetadata(null);
  }, []);

  const dismissError = useCallback(() => {
    setError(null);
    setRetryText(null);
  }, []);

  return {
    sessionId,
    messages,
    input,
    setInput,
    isSending,
    error,
    canRetry: Boolean(retryText),
    lastMetadata,
    send,
    retry,
    newSession,
    dismissError,
  };
}
