"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Session {
  id: number;
  title: string;
  status: "pending" | "transcribing" | "done" | "error";
  duration_secs: number | null;
  error_msg: string | null;
  created_at: string;
}

const STATUS_LABELS: Record<Session["status"], string> = {
  pending: "Pending",
  transcribing: "Transcribing",
  done: "Done",
  error: "Error",
};

const STATUS_COLORS: Record<Session["status"], string> = {
  pending: "var(--status-pending)",
  transcribing: "var(--status-transcribing)",
  done: "var(--status-done)",
  error: "var(--status-error)",
};

function formatDuration(secs: number | null) {
  if (!secs) return "—";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetch("/api/sessions")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        setSessions(data.sessions ?? data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  function toggleSelect(id: number, e: React.MouseEvent) {
    e.preventDefault();
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selected.size === sessions.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(sessions.map((s) => s.id)));
    }
  }

  async function deleteSelected() {
    if (selected.size === 0) return;
    setDeleting(true);
    await Promise.all(
      [...selected].map((id) =>
        fetch(`/api/sessions/${id}`, { method: "DELETE" })
      )
    );
    setSessions((prev) => prev.filter((s) => !selected.has(s.id)));
    setSelected(new Set());
    setDeleting(false);
  }

  const allSelected = sessions.length > 0 && selected.size === sessions.length;
  const someSelected = selected.size > 0;

  return (
    <div style={{ padding: "40px 48px", maxWidth: "900px" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: "32px",
          gap: "16px",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "22px",
              fontWeight: 600,
              color: "var(--foreground)",
              margin: 0,
              letterSpacing: "-0.02em",
            }}
          >
            Sessions
          </h1>
          <p style={{ fontSize: "13px", color: "var(--muted)", margin: "4px 0 0" }}>
            Your recorded and transcribed meetings
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
          {someSelected && (
            <button
              onClick={deleteSelected}
              disabled={deleting}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 14px",
                background: "rgba(239,68,68,0.1)",
                border: "1px solid rgba(239,68,68,0.3)",
                borderRadius: "6px",
                color: "var(--status-error)",
                fontSize: "13px",
                fontWeight: 500,
                cursor: deleting ? "not-allowed" : "pointer",
                opacity: deleting ? 0.6 : 1,
              }}
            >
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path d="M2 3.5h9M5 3.5V2.5a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 .5.5v1M10.5 3.5l-.5 7a1 1 0 0 1-1 .93H4a1 1 0 0 1-1-.93l-.5-7" strokeLinecap="round" />
              </svg>
              {deleting ? "Deleting…" : `Delete ${selected.size}`}
            </button>
          )}
          <Link
            href="/record"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 16px",
              background: "var(--accent)",
              color: "#fff",
              borderRadius: "6px",
              fontSize: "13px",
              fontWeight: 500,
              textDecoration: "none",
              letterSpacing: "-0.01em",
            }}
          >
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="4" y="1" width="5" height="7.5" rx="2.5" />
              <path d="M2 6a4.5 4.5 0 0 0 9 0" />
              <line x1="6.5" y1="11.5" x2="6.5" y2="10.5" />
              <line x1="4.5" y1="12" x2="8.5" y2="12" />
            </svg>
            New Recording
          </Link>
        </div>
      </div>

      {/* Content */}
      {loading && (
        <div style={{ color: "var(--muted)", fontSize: "14px" }}>Loading…</div>
      )}

      {error && (
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
          Failed to load sessions: {error}
        </div>
      )}

      {!loading && !error && sessions.length === 0 && (
        <div style={{ padding: "64px 0", textAlign: "center" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "12px",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 20px",
            }}
          >
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="var(--muted)" strokeWidth="1.5">
              <rect x="5.5" y="1.5" width="11" height="15" rx="2.5" />
              <path d="M3 9a8 8 0 0 0 16 0" />
              <line x1="11" y1="19" x2="11" y2="17" />
              <line x1="8" y1="20" x2="14" y2="20" />
            </svg>
          </div>
          <p style={{ fontSize: "15px", fontWeight: 500, color: "var(--foreground)", margin: "0 0 8px" }}>
            No sessions yet
          </p>
          <p style={{ fontSize: "13px", color: "var(--muted)", margin: "0 0 24px" }}>
            Record your first meeting to get started
          </p>
          <Link
            href="/record"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 20px",
              background: "var(--accent)",
              color: "#fff",
              borderRadius: "6px",
              fontSize: "14px",
              fontWeight: 500,
              textDecoration: "none",
            }}
          >
            Start Recording
          </Link>
        </div>
      )}

      {!loading && !error && sessions.length > 0 && (
        <div style={{ border: "1px solid var(--border)", borderRadius: "8px", overflow: "hidden" }}>
          {/* Select-all header row */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "40px 1fr",
              alignItems: "center",
              padding: "10px 20px 10px 0",
              borderBottom: "1px solid var(--border)",
              background: "var(--surface)",
            }}
          >
            <div
              style={{ display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}
              onClick={toggleSelectAll}
            >
              <Checkbox checked={allSelected} indeterminate={someSelected && !allSelected} />
            </div>
            <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-geist-mono)", letterSpacing: "0.04em" }}>
              {someSelected ? `${selected.size} selected` : `${sessions.length} session${sessions.length !== 1 ? "s" : ""}`}
            </span>
          </div>

          {sessions.map((session, i) => {
            const isSelected = selected.has(session.id);
            return (
              <div
                key={session.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "40px 1fr auto auto auto",
                  alignItems: "center",
                  gap: "0",
                  borderBottom: i < sessions.length - 1 ? "1px solid var(--border)" : "none",
                  background: isSelected ? "rgba(249,115,22,0.06)" : "var(--surface)",
                  transition: "background 0.1s",
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) e.currentTarget.style.background = "var(--surface-hover)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = isSelected ? "rgba(249,115,22,0.06)" : "var(--surface)";
                }}
              >
                {/* Checkbox */}
                <div
                  style={{ display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", padding: "14px 0", alignSelf: "stretch" }}
                  onClick={(e) => toggleSelect(session.id, e)}
                >
                  <Checkbox checked={isSelected} />
                </div>

                {/* Title + date — navigates */}
                <Link
                  href={`/sessions/${session.id}`}
                  style={{ display: "block", padding: "14px 16px 14px 4px", textDecoration: "none", color: "inherit" }}
                >
                  <div style={{ fontSize: "14px", fontWeight: 500, color: "var(--foreground)", marginBottom: "3px" }}>
                    {session.title}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--muted)", fontFamily: "var(--font-geist-mono)" }}>
                    {formatDate(session.created_at)}
                  </div>
                </Link>

                {/* Duration */}
                <div style={{ fontSize: "12px", color: "var(--muted)", fontFamily: "var(--font-geist-mono)", minWidth: "48px", textAlign: "right", padding: "0 16px" }}>
                  {formatDuration(session.duration_secs)}
                </div>

                {/* Status badge */}
                <div
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
                    background: `${STATUS_COLORS[session.status]}18`,
                    color: STATUS_COLORS[session.status],
                    border: `1px solid ${STATUS_COLORS[session.status]}40`,
                    marginRight: "16px",
                  }}
                >
                  <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: STATUS_COLORS[session.status], flexShrink: 0 }} />
                  {STATUS_LABELS[session.status]}
                </div>

                {/* Arrow */}
                <Link href={`/sessions/${session.id}`} style={{ display: "flex", alignItems: "center", padding: "0 20px 0 0", color: "inherit" }}>
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--muted)" strokeWidth="1.5">
                    <path d="M5 3l4 4-4 4" />
                  </svg>
                </Link>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Checkbox({ checked, indeterminate }: { checked: boolean; indeterminate?: boolean }) {
  return (
    <div
      style={{
        width: "16px",
        height: "16px",
        borderRadius: "4px",
        border: checked || indeterminate ? "1.5px solid var(--accent)" : "1.5px solid var(--muted)",
        background: checked || indeterminate ? "var(--accent)" : "transparent",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        transition: "background 0.1s, border-color 0.1s",
      }}
    >
      {indeterminate && !checked && (
        <svg width="8" height="2" viewBox="0 0 8 2" fill="none">
          <line x1="0" y1="1" x2="8" y2="1" stroke="white" strokeWidth="2" strokeLinecap="round" />
        </svg>
      )}
      {checked && (
        <svg width="9" height="7" viewBox="0 0 9 7" fill="none">
          <path d="M1 3.5l2.5 2.5 5-5" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </div>
  );
}
