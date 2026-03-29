"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

type RecordState = "idle" | "recording" | "uploading" | "done" | "error";

function formatElapsed(secs: number) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function RecordPage() {
  const router = useRouter();
  const [state, setState] = useState<RecordState>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      });

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const mr = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 128000,
      });
      chunksRef.current = [];
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.start(1000);
      mediaRecorderRef.current = mr;
      setState("recording");
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((n) => n + 1), 1000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Microphone access denied");
      setState("error");
    }
  }

  async function stopAndUpload() {
    const mr = mediaRecorderRef.current;
    if (!mr) return;

    setState("uploading");
    if (timerRef.current) clearInterval(timerRef.current);

    await new Promise<void>((resolve) => {
      mr.onstop = () => resolve();
      mr.stop();
      mr.stream.getTracks().forEach((t) => t.stop());
    });

    const mimeType = chunksRef.current[0]?.type || "audio/webm";
    const ext = mimeType.includes("ogg") ? "ogg" : "webm";
    const blob = new Blob(chunksRef.current, { type: mimeType });
    const file = new File([blob], `recording.${ext}`, { type: mimeType });

    const form = new FormData();
    form.append("file", file);
    if (title.trim()) form.append("title", title.trim());

    try {
      const res = await fetch("/api/sessions/upload", {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Upload failed (${res.status}): ${text}`);
      }
      const data = await res.json();
      setState("done");
      setTimeout(() => router.push(`/sessions/${data.session_id}`), 600);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setState("error");
    }
  }

  return (
    <div
      style={{
        padding: "40px 48px",
        maxWidth: "600px",
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: "40px" }}>
        <h1
          style={{
            fontSize: "22px",
            fontWeight: 600,
            color: "var(--foreground)",
            margin: "0 0 6px",
            letterSpacing: "-0.02em",
          }}
        >
          New Recording
        </h1>
        <p style={{ fontSize: "13px", color: "var(--muted)", margin: 0 }}>
          Audio is recorded locally and transcribed on-device
        </p>
      </div>

      {/* Title input */}
      <div style={{ marginBottom: "32px" }}>
        <label
          style={{
            display: "block",
            fontSize: "12px",
            fontWeight: 500,
            color: "var(--muted-light)",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            marginBottom: "8px",
            fontFamily: "var(--font-geist-mono)",
          }}
        >
          Session Title
        </label>
        <input
          type="text"
          placeholder="Weekly standup, Design review…"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={state === "recording" || state === "uploading"}
          style={{
            width: "100%",
            padding: "10px 14px",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "6px",
            color: "var(--foreground)",
            fontSize: "14px",
            fontFamily: "var(--font-geist-sans)",
            outline: "none",
          }}
        />
      </div>

      {/* Recorder */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "10px",
          padding: "40px",
          textAlign: "center",
        }}
      >
        {/* Timer display */}
        <div
          style={{
            fontFamily: "var(--font-geist-mono)",
            fontSize: "48px",
            fontWeight: 300,
            letterSpacing: "0.04em",
            color:
              state === "recording" ? "var(--foreground)" : "var(--muted)",
            marginBottom: "32px",
            transition: "color 0.2s",
          }}
        >
          {formatElapsed(elapsed)}
        </div>

        {/* Record button */}
        {state === "idle" || state === "error" ? (
          <button
            onClick={startRecording}
            style={{
              width: "72px",
              height: "72px",
              borderRadius: "50%",
              background: "var(--accent)",
              border: "none",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "transform 0.1s, opacity 0.1s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.85")}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <rect x="9" y="2" width="6" height="13" rx="3" />
              <path d="M5 11a7 7 0 0 0 14 0" />
              <line x1="12" y1="20" x2="12" y2="18" />
              <line x1="9" y1="22" x2="15" y2="22" />
            </svg>
          </button>
        ) : state === "recording" ? (
          <button
            onClick={stopAndUpload}
            style={{
              width: "72px",
              height: "72px",
              borderRadius: "50%",
              background: "var(--status-error)",
              border: "4px solid rgba(239,68,68,0.3)",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              animation: "pulse 2s infinite",
            }}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="white">
              <rect x="4" y="4" width="12" height="12" rx="2" />
            </svg>
          </button>
        ) : state === "uploading" ? (
          <div
            style={{
              width: "72px",
              height: "72px",
              borderRadius: "50%",
              background: "var(--surface-hover)",
              border: "1px solid var(--border)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="var(--status-transcribing)" strokeWidth="2">
              <path d="M11 2a9 9 0 1 0 9 9" strokeLinecap="round">
                <animateTransform attributeName="transform" type="rotate" from="0 11 11" to="360 11 11" dur="0.8s" repeatCount="indefinite" />
              </path>
            </svg>
          </div>
        ) : state === "done" ? (
          <div
            style={{
              width: "72px",
              height: "72px",
              borderRadius: "50%",
              background: `${STATUS_COLOR_DONE}18`,
              border: `1px solid ${STATUS_COLOR_DONE}40`,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--status-done)" strokeWidth="2.5">
              <path d="M5 13l5 5L19 7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        ) : null}

        {/* Status text */}
        <div
          style={{
            marginTop: "20px",
            fontSize: "13px",
            color: "var(--muted)",
          }}
        >
          {state === "idle" && "Tap to start recording"}
          {state === "recording" && "Recording — tap to stop & upload"}
          {state === "uploading" && "Uploading and queuing transcription…"}
          {state === "done" && "Done — redirecting to transcript…"}
          {state === "error" && (
            <span style={{ color: "var(--status-error)" }}>
              {error ?? "Unknown error"}
            </span>
          )}
        </div>
      </div>

      {/* Pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }
          50% { box-shadow: 0 0 0 10px rgba(239,68,68,0); }
        }
      `}</style>
    </div>
  );
}

const STATUS_COLOR_DONE = "#22c55e";
