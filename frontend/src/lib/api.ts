import type {
  ChatMetadata,
  ChatResponse,
  HealthResponse,
  SessionMessagesResponse,
} from "../types";

const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim();
export const API_BASE_URL = (configuredBase || "http://localhost:8000").replace(
  /\/+$/,
  "",
);

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, body: unknown) {
    super(`API request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function request<T>(
  path: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...init.headers,
      },
    });

    const text = await response.text();
    let body: unknown = null;
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = text;
      }
    }

    if (!response.ok) {
      throw new ApiError(response.status, body);
    }

    return body as T;
  } finally {
    window.clearTimeout(timeout);
  }
}

export interface ChatRequestPayload {
  session_id: string;
  message: string;
  system_prompt?: string;
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health", { method: "GET" }, 8_000);
}

export function sendChat(payload: ChatRequestPayload): Promise<ChatResponse> {
  return request<ChatResponse>(
    "/chat",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    90_000,
  );
}

export function fetchSessionMessages(
  sessionId: string,
): Promise<SessionMessagesResponse> {
  return request<SessionMessagesResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/messages`,
    { method: "GET" },
    15_000,
  );
}

function validationMessage(body: unknown): string | null {
  if (!body || typeof body !== "object" || !("detail" in body)) {
    return null;
  }

  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (!Array.isArray(detail)) {
    return null;
  }

  const messages = detail
    .map((item) => {
      if (typeof item === "string") {
        return item;
      }
      if (item && typeof item === "object" && "msg" in item) {
        const msg = (item as { msg: unknown }).msg;
        if (typeof msg === "string") {
          return msg.replace(/^Value error,\s*/i, "");
        }
      }
      return null;
    })
    .filter((message): message is string => Boolean(message));

  return messages.length > 0 ? messages.join(" ") : null;
}

export function describeApiError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 422) {
      return (
        validationMessage(error.body) ??
        "That request could not be accepted. Check the message and try again."
      );
    }
    if (error.status === 503) {
      return "All providers are temporarily unavailable. Your message was not saved. Try again in a moment.";
    }
    if (error.status === 404) {
      return "This session could not be found. Start a new session and try again.";
    }
    return `The request failed (HTTP ${error.status}). Your message was not saved.`;
  }

  if (
    error instanceof DOMException &&
    (error.name === "AbortError" || error.name === "TimeoutError")
  ) {
    return "The request timed out. Your message was not saved. Please try again.";
  }

  return `Could not reach the LYFTR AI API at ${API_BASE_URL}. Check that the backend is running.`;
}

export type { ChatMetadata };
