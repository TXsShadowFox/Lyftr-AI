export function createSessionId(): string {
  const random =
    globalThis.crypto?.randomUUID?.() ??
    Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
  return `s-${random.replace(/-/g, "").slice(0, 12)}`;
}

export function shortSessionId(sessionId: string): string {
  return sessionId.length > 16 ? `${sessionId.slice(0, 16)}…` : sessionId;
}
