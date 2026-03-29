"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

interface Session {
  id: number;
  title: string;
  status: "pending" | "transcribing" | "done" | "error";
  duration_secs: number | null;
  error_msg: string | null;
  created_at: string;
  updated_at: string;
}

interface Segment {
  id: number;
  sequence_num: number;
  text: string;
  start_sec: number;
  end_sec: number;
  speaker: string | null;
}

const STATUS_COLORS = {
  pending: "var(--status-pending)",
  transcribing: "var(--status-transcribing)",
  done: "var(--status-done)",
  error: "var(--status-error)",
};

const STATUS_LABELS = {
  pending: "Pending",
  transcribing: "Transcribing",
  done: "Done",
  error: "Error",
};

function formatTime(secs: number) {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatDuration(secs: number | null) {
  if (!secs) return null;
  return formatTime(secs);
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [session, setSession] = useState<Session | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [savingTitle, setSavingTitle] = useState(false);
  const titleInputRef = useRef<HTMLInputElement | null>(null);

  async function fetchSession() {
    const res = await fetch(`/api/sessions/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json() as Promise<Session>;
  }

  async function fetchSegments() {
    const res = await fetch(`/api/sessions/${id}/segments`);
    if (!res.ok) return [];
    const data = await res.json();
    return (data.segments ?? data) as Segment[];
  }

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [s, segs] = await Promise.all([fetchSession(), fetchSegments()]);
        if (cancelled) return;
        setSession(s);
        setSegments(segs);

        if (s.status === "pending" || s.status === "transcribing") {
          pollRef.current = setInterval(async () => {
            try {
              const [updated, updatedSegs] = await Promise.all([
                fetchSession(),
                fetchSegments(),
              ]);
              if (cancelled) return;
              setSession(updated);
              setSegments(updatedSegs);
              if (updated.status === "done" || updated.status === "error") {
                if (pollRef.current) clearInterval(pollRef.current);
              }
            } catch {}
          }, 2000);
        }
      } catch (e) {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : "Failed to load");
        }
      }
    }

    load();
    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [id]);

  async function handleDelete() {
    if (!confirm("Delete this session?")) return;
    await fetch(`/api/sessions/${id}`, { method: "DELETE" });
    router.push("/");
  }

  function startEditTitle() {
    if (!session) return;
    setTitleDraft(session.title);
    setEditingTitle(true);
    setTimeout(() => titleInputRef.current?.select(), 0);
  }

  async function saveTitle() {
    if (!session || !titleDraft.trim() || titleDraft.trim() === session.title) {
      setEditingTitle(false);
      return;
    }
    setSavingTitle(true);
    const res = await fetch(`/api/sessions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: titleDraft.trim() }),
    });
    if (res.ok) {
      const updated = await res.json();
      setSession(updated);
    }
    setSavingTitle(false);
    setEditingTitle(false);
  }

  function handleTitleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") saveTitle();
    if (e.key === "Escape") setEditingTitle(false);
  }

  if (loadError) {
    return (
      <div style={{ padding: "40px 48px" }}>
        <div
          style={{
            padding: "14px 18px",
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: "6px",
            color: "var(--status-error)",
            fontSize: "13px",
          }}
        >
          {loadError}
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div style={{ padding: "40px 48px", color: "var(--muted)", fontSize: "14px" }}>
        Loading…
      </div>
    );
  }

  const statusColor = STATUS_COLORS[session.status];

  return (
    <div style={{ padding: "40px 48px", maxWidth: "860px" }}>
      {/* Back + title row */}
      <div style={{ marginBottom: "8px" }}>
        <Link
          href="/"
          style={{
            fontSize: "12px",
            color: "var(--muted)",
            textDecoration: "none",
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
          }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M8 2L4 6l4 4" strokeLinecap="round" />
          </svg>
          Sessions
        </Link>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "24px",
          marginBottom: "32px",
        }}
      >
        <div>
          {editingTitle ? (
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
              <input
                ref={titleInputRef}
                value={titleDraft}
                onChange={(e) => setTitleDraft(e.target.value)}
                onKeyDown={handleTitleKeyDown}
                onBlur={saveTitle}
                autoFocus
                style={{
                  fontSize: "22px",
                  fontWeight: 600,
                  letterSpacing: "-0.02em",
                  color: "var(--foreground)",
                  background: "var(--surface)",
                  border: "1px solid var(--accent)",
                  borderRadius: "6px",
                  padding: "2px 10px",
                  outline: "none",
                  fontFamily: "var(--font-geist-sans)",
                  minWidth: "280px",
                }}
              />
              <button
                onClick={saveTitle}
                disabled={savingTitle}
                style={{ padding: "4px 12px", background: "var(--accent)", color: "#fff", border: "none", borderRadius: "5px", fontSize: "12px", fontWeight: 500, cursor: "pointer" }}
              >
                {savingTitle ? "Saving…" : "Save"}
              </button>
              <button
                onClick={() => setEditingTitle(false)}
                style={{ padding: "4px 10px", background: "transparent", color: "var(--muted)", border: "1px solid var(--border)", borderRadius: "5px", fontSize: "12px", cursor: "pointer" }}
              >
                Cancel
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
              <h1
                style={{
                  fontSize: "22px",
                  fontWeight: 600,
                  color: "var(--foreground)",
                  margin: 0,
                  letterSpacing: "-0.02em",
                }}
              >
                {session.title}
              </h1>
              <button
                onClick={startEditTitle}
                title="Edit title"
                style={{ background: "transparent", border: "none", cursor: "pointer", color: "var(--muted)", padding: "4px", display: "flex", alignItems: "center", borderRadius: "4px" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "var(--foreground)")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "var(--muted)")}
              >
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M9 1.5l2.5 2.5-7 7H2V8.5l7-7z" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
          )}

          {/* Meta row */}
          <div style={{ display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
            {/* Status */}
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                padding: "3px 8px",
                borderRadius: "4px",
                fontSize: "11px",
                fontWeight: 500,
                fontFamily: "var(--font-geist-mono)",
                letterSpacing: "0.04em",
                background: `${statusColor}18`,
                color: statusColor,
                border: `1px solid ${statusColor}40`,
              }}
            >
              <span
                style={{
                  width: "5px",
                  height: "5px",
                  borderRadius: "50%",
                  background: statusColor,
                  flexShrink: 0,
                  ...(session.status === "transcribing"
                    ? { animation: "blink 1.2s infinite" }
                    : {}),
                }}
              />
              {STATUS_LABELS[session.status]}
            </span>

            {/* Duration */}
            {formatDuration(session.duration_secs) && (
              <span
                style={{
                  fontSize: "12px",
                  color: "var(--muted)",
                  fontFamily: "var(--font-geist-mono)",
                }}
              >
                {formatDuration(session.duration_secs)}
              </span>
            )}

            {/* Date */}
            <span
              style={{
                fontSize: "12px",
                color: "var(--muted)",
              }}
            >
              {formatDate(session.created_at)}
            </span>
          </div>
        </div>

        <button
          onClick={handleDelete}
          style={{
            padding: "7px 12px",
            background: "transparent",
            border: "1px solid var(--border)",
            borderRadius: "6px",
            color: "var(--muted)",
            fontSize: "12px",
            cursor: "pointer",
            flexShrink: 0,
            transition: "border-color 0.15s, color 0.15s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "var(--status-error)";
            e.currentTarget.style.color = "var(--status-error)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "var(--border)";
            e.currentTarget.style.color = "var(--muted)";
          }}
        >
          Delete
        </button>
      </div>

      {/* Error message */}
      {session.status === "error" && session.error_msg && (
        <div
          style={{
            padding: "14px 18px",
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: "6px",
            color: "var(--status-error)",
            fontSize: "13px",
            marginBottom: "24px",
          }}
        >
          Transcription error: {session.error_msg}
        </div>
      )}

      {/* In-progress state */}
      {(session.status === "pending" || session.status === "transcribing") && (
        <div
          style={{
            padding: "32px",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            textAlign: "center",
            marginBottom: "24px",
          }}
        >
          <div
            style={{
              width: "36px",
              height: "36px",
              margin: "0 auto 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="var(--status-transcribing)" strokeWidth="2">
              <path d="M14 3a11 11 0 1 0 11 11" strokeLinecap="round">
                <animateTransform attributeName="transform" type="rotate" from="0 14 14" to="360 14 14" dur="1s" repeatCount="indefinite" />
              </path>
            </svg>
          </div>
          <p
            style={{
              fontSize: "14px",
              color: "var(--foreground)",
              margin: "0 0 4px",
              fontWeight: 500,
            }}
          >
            {session.status === "pending"
              ? "Queued for transcription"
              : "Transcribing audio…"}
          </p>
          <p style={{ fontSize: "13px", color: "var(--muted)", margin: 0 }}>
            This page will update automatically
          </p>
        </div>
      )}

      {/* Transcript */}
      {segments.length > 0 && (
        <div>
          <div
            style={{
              fontSize: "11px",
              fontWeight: 500,
              color: "var(--muted)",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              fontFamily: "var(--font-geist-mono)",
              marginBottom: "16px",
            }}
          >
            Transcript · {segments.length} segments
          </div>

          <div
            style={{
              border: "1px solid var(--border)",
              borderRadius: "8px",
              overflow: "hidden",
            }}
          >
            {segments.map((seg, i) => (
              <div
                key={seg.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "72px 1fr",
                  gap: "0",
                  borderBottom:
                    i < segments.length - 1 ? "1px solid var(--border)" : "none",
                }}
              >
                {/* Timestamp */}
                <div
                  style={{
                    padding: "14px 16px",
                    fontSize: "11px",
                    fontFamily: "var(--font-geist-mono)",
                    color: "var(--muted)",
                    borderRight: "1px solid var(--border)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "4px",
                    background: "var(--surface)",
                  }}
                >
                  <span>{formatTime(seg.start_sec)}</span>
                  <span style={{ opacity: 0.5 }}>{formatTime(seg.end_sec)}</span>
                </div>

                {/* Text */}
                <div
                  style={{
                    padding: "14px 20px",
                    fontSize: "14px",
                    lineHeight: "1.65",
                    color: "var(--foreground)",
                    background: i % 2 === 0 ? "var(--surface)" : "var(--background)",
                  }}
                >
                  {seg.speaker && (
                    <span
                      style={{
                        fontSize: "11px",
                        fontFamily: "var(--font-geist-mono)",
                        color: "var(--accent)",
                        marginBottom: "4px",
                        display: "block",
                        fontWeight: 500,
                      }}
                    >
                      {seg.speaker}
                    </span>
                  )}
                  {seg.text}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Done but no segments */}
      {session.status === "done" && segments.length === 0 && (
        <div
          style={{
            padding: "32px",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            textAlign: "center",
            color: "var(--muted)",
            fontSize: "14px",
          }}
        >
          No transcript segments found
        </div>
      )}

      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}
