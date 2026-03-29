"use client";

import { useEffect, useRef, useState } from "react";

interface HealthData {
  status: string;
  model_id: string;
  model_cached: boolean;
  model_loaded: boolean;
}

type BackendState = "connecting" | "online" | "offline";

const POLL_INTERVAL_MS = 5000;

export default function StatusBar() {
  const [backend, setBackend] = useState<BackendState>("connecting");
  const [health, setHealth] = useState<HealthData | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function poll() {
    try {
      const res = await fetch("/api/health", { signal: AbortSignal.timeout(3000) });
      if (!res.ok) throw new Error();
      const data: HealthData = await res.json();
      setHealth(data);
      setBackend("online");
    } catch {
      setBackend("offline");
      setHealth(null);
    }
  }

  useEffect(() => {
    poll();
    timerRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const modelShortId = health?.model_id.split("/").pop() ?? "";

  type Indicator = { dot: string; label: string; title: string };

  const backendIndicator: Indicator =
    backend === "connecting"
      ? { dot: "var(--status-pending)", label: "Connecting…", title: "Connecting to backend" }
      : backend === "offline"
      ? { dot: "var(--status-error)", label: "Backend offline", title: "Backend not reachable — is it running?" }
      : { dot: "var(--status-done)", label: "Backend", title: "Backend is running" };

  const modelIndicator: Indicator | null =
    backend !== "online"
      ? null
      : !health?.model_cached
      ? { dot: "var(--status-error)", label: `${modelShortId} not found`, title: "Run: uv run python scripts/setup_models.py" }
      : !health?.model_loaded
      ? { dot: "var(--status-pending)", label: `${modelShortId} loading…`, title: "Model is downloading or loading into memory" }
      : { dot: "var(--status-done)", label: modelShortId, title: "Whisper model ready" };

  const indicators = [backendIndicator, ...(modelIndicator ? [modelIndicator] : [])];

  return (
    <div
      style={{
        position: "fixed",
        bottom: 0,
        left: "220px", // sidebar width
        right: 0,
        height: "28px",
        background: "var(--sidebar-bg)",
        borderTop: "1px solid var(--sidebar-border)",
        display: "flex",
        alignItems: "center",
        gap: "2px",
        padding: "0 16px",
        zIndex: 50,
      }}
    >
      {indicators.map((ind, i) => (
        <div
          key={i}
          title={ind.title}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "5px",
            padding: "0 8px",
            height: "20px",
            borderRadius: "4px",
            cursor: "default",
            transition: "background 0.15s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: ind.dot,
              flexShrink: 0,
              ...(ind.dot === "var(--status-pending)"
                ? { animation: "sb-pulse 1.4s ease-in-out infinite" }
                : {}),
            }}
          />
          <span
            style={{
              fontSize: "11px",
              fontFamily: "var(--font-geist-mono)",
              color: "var(--muted)",
              letterSpacing: "0.02em",
              whiteSpace: "nowrap",
            }}
          >
            {ind.label}
          </span>
        </div>
      ))}

      {/* Separator */}
      {indicators.length > 1 && (
        <span style={{ width: "1px", height: "12px", background: "var(--border)", margin: "0 2px" }} />
      )}

      <style>{`
        @keyframes sb-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.35; }
        }
      `}</style>
    </div>
  );
}
