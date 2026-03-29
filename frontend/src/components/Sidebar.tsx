"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  {
    href: "/",
    label: "Sessions",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="1.5" y="2.5" width="13" height="11" rx="1.5" />
        <line x1="4.5" y1="6" x2="11.5" y2="6" />
        <line x1="4.5" y1="8.5" x2="9" y2="8.5" />
        <line x1="4.5" y1="11" x2="7.5" y2="11" />
      </svg>
    ),
  },
  {
    href: "/record",
    label: "Record",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="5" y="1.5" width="6" height="9" rx="3" />
        <path d="M2.5 8.5a5.5 5.5 0 0 0 11 0" />
        <line x1="8" y1="14" x2="8" y2="13.5" />
        <line x1="5.5" y1="14.5" x2="10.5" y2="14.5" />
      </svg>
    ),
  },
  {
    href: "/chat",
    label: "Chat",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M1.5 2.5h13a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H5l-3.5 2.5V3.5a1 1 0 0 1 1-1z" />
      </svg>
    ),
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const stored = localStorage.getItem("theme") as "dark" | "light" | null;
    const active = stored ?? "dark";
    setTheme(active);
    document.documentElement.classList.toggle("dark", active === "dark");
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("theme", next);
    document.documentElement.classList.toggle("dark", next === "dark");
  }

  return (
    <aside
      style={{
        width: "220px",
        minWidth: "220px",
        background: "var(--sidebar-bg)",
        borderRight: "1px solid var(--sidebar-border)",
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        position: "sticky",
        top: 0,
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: "24px 20px 20px",
          borderBottom: "1px solid var(--sidebar-border)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "28px",
              height: "28px",
              background: "var(--accent)",
              borderRadius: "6px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="white" strokeWidth="1.8">
              <rect x="1.5" y="2" width="11" height="9" rx="1.5" />
              <path d="M4.5 7a2.5 2.5 0 0 0 5 0" />
              <circle cx="7" cy="5" r="1" fill="white" stroke="none" />
            </svg>
          </div>
          <div>
            <div
              style={{
                fontSize: "13px",
                fontWeight: 600,
                color: "var(--foreground)",
                letterSpacing: "-0.01em",
                lineHeight: 1.2,
              }}
            >
              Meeting
            </div>
            <div
              style={{
                fontSize: "11px",
                color: "var(--muted)",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                fontFamily: "var(--font-geist-mono)",
              }}
            >
              Assistant
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ padding: "12px 8px", flex: 1 }}>
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/" || pathname.startsWith("/sessions")
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "8px 12px",
                borderRadius: "6px",
                marginBottom: "2px",
                color: isActive ? "var(--foreground)" : "var(--muted-light)",
                background: isActive ? "var(--surface)" : "transparent",
                borderLeft: isActive ? "2px solid var(--accent)" : "2px solid transparent",
                fontSize: "14px",
                fontWeight: isActive ? 500 : 400,
                textDecoration: "none",
                transition: "background 0.15s, color 0.15s",
              }}
            >
              <span style={{ opacity: isActive ? 1 : 0.7 }}>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div
        style={{
          padding: "12px 16px",
          borderTop: "1px solid var(--sidebar-border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-geist-mono)" }}>
          local · on-device
        </span>
        <button
          onClick={toggleTheme}
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            borderRadius: "6px",
            color: "var(--muted)",
            cursor: "pointer",
            padding: "5px 6px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "color 0.15s, border-color 0.15s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = "var(--foreground)";
            e.currentTarget.style.borderColor = "var(--muted)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = "var(--muted)";
            e.currentTarget.style.borderColor = "var(--border)";
          }}
        >
          {theme === "dark" ? (
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="6.5" cy="6.5" r="2.5" />
              <line x1="6.5" y1="1" x2="6.5" y2="2.2" strokeLinecap="round" />
              <line x1="6.5" y1="10.8" x2="6.5" y2="12" strokeLinecap="round" />
              <line x1="1" y1="6.5" x2="2.2" y2="6.5" strokeLinecap="round" />
              <line x1="10.8" y1="6.5" x2="12" y2="6.5" strokeLinecap="round" />
              <line x1="2.8" y1="2.8" x2="3.65" y2="3.65" strokeLinecap="round" />
              <line x1="9.35" y1="9.35" x2="10.2" y2="10.2" strokeLinecap="round" />
              <line x1="10.2" y1="2.8" x2="9.35" y2="3.65" strokeLinecap="round" />
              <line x1="3.65" y1="9.35" x2="2.8" y2="10.2" strokeLinecap="round" />
            </svg>
          ) : (
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M10.5 7.5A5 5 0 0 1 5.5 2.5a5 5 0 1 0 5 5z" strokeLinejoin="round" />
            </svg>
          )}
        </button>
      </div>
    </aside>
  );
}
