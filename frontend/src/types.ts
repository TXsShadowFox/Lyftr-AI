export type ResolutionSource = "LIVE_INFERENCE" | "LLM_CACHE";

export interface ChatMetadata {
  resolution_source: ResolutionSource;
  model: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  key_id: string | null;
  fallback_attempts: number;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  metadata: ChatMetadata;
}

export interface HealthResponse {
  status: "ok" | "error";
  keys_configured: number;
  cache_enabled: boolean;
  detail?: string;
}

export interface StoredMessage {
  role: "user" | "assistant";
  content: string;
  metadata?: ChatMetadata;
}

export interface SessionMessagesResponse {
  session_id: string;
  messages: StoredMessage[];
}

export type UiMessage =
  | { id: string; role: "user"; content: string }
  | { id: string; role: "assistant"; content: string; metadata: ChatMetadata };
