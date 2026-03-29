import type { HealthSnapshot, LlmSettingsOut, ModelsResponse, SegmentOut, SessionOut } from "./types";

const json = async (r: Response) => {
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || r.statusText);
  }
  return r.json() as Promise<unknown>;
};

export async function fetchHealth(): Promise<HealthSnapshot> {
  const r = await fetch("/api/health");
  return json(r) as Promise<HealthSnapshot>;
}

export async function fetchModels(): Promise<ModelsResponse> {
  const r = await fetch("/api/models");
  return json(r) as Promise<ModelsResponse>;
}

export async function fetchLlmSettings(): Promise<LlmSettingsOut> {
  const r = await fetch("/api/settings/llm");
  return json(r) as Promise<LlmSettingsOut>;
}

export async function patchLlmSettings(body: {
  model_id: string | null;
  max_new_tokens: number | null;
}): Promise<LlmSettingsOut> {
  const r = await fetch("/api/settings/llm", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return json(r) as Promise<LlmSettingsOut>;
}

export async function summarizeSession(
  sessionId: number,
  maxChars?: number,
): Promise<{ summary: string; llm_model: string }> {
  const r = await fetch(`/api/sessions/${sessionId}/summarize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(maxChars != null ? { max_chars: maxChars } : {}),
  });
  return json(r) as Promise<{ summary: string; llm_model: string }>;
}

export async function fetchSessions(sessionType?: string): Promise<SessionOut[]> {
  const q =
    sessionType && sessionType !== "all"
      ? `?session_type=${encodeURIComponent(sessionType)}`
      : "";
  const r = await fetch(`/api/sessions${q}`);
  return json(r) as Promise<SessionOut[]>;
}

export async function deleteSession(id: number): Promise<void> {
  const r = await fetch(`/api/sessions/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(await r.text());
}

export async function fetchSegments(sessionId: number): Promise<SegmentOut[]> {
  const r = await fetch(`/api/sessions/${sessionId}/segments`);
  return json(r) as Promise<SegmentOut[]>;
}

export async function postReindex(sessionId: number): Promise<{ indexed_chunks: number }> {
  const r = await fetch(`/api/sessions/${sessionId}/reindex`, { method: "POST" });
  return json(r) as Promise<{ indexed_chunks: number }>;
}

export async function* streamChat(
  sessionId: number,
  message: string,
  chatSessionId?: number | null,
): AsyncGenerator<Record<string, unknown>, void, unknown> {
  const r = await fetch(`/api/sessions/${sessionId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      chat_session_id: chatSessionId ?? null,
    }),
  });
  if (!r.ok || !r.body) {
    throw new Error(await r.text());
  }
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const chunks = buf.split("\n\n");
    buf = chunks.pop() ?? "";
    for (const block of chunks) {
      const line = block.trim();
      if (!line.startsWith("data: ")) continue;
      const data = JSON.parse(line.slice(6)) as Record<string, unknown>;
      yield data;
    }
  }
  const tail = buf.trim();
  if (tail.startsWith("data: ")) {
    yield JSON.parse(tail.slice(6)) as Record<string, unknown>;
  }
}

export function formatDuration(secs: number | null): string {
  if (secs == null) return "—";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return m > 0 ? `${m}m ${s.toString().padStart(2, "0")}s` : `${s}s`;
}
