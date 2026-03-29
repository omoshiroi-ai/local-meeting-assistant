import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Sidebar from "@/components/Sidebar";
import StatusBar from "@/components/StatusBar";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Meeting Assistant",
  description: "Local-first meeting recorder and transcriber",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable}`}
    >
      <body
        style={{
          display: "flex",
          height: "100vh",
          overflow: "hidden",
          margin: 0,
        }}
      >
        <Sidebar />
        <main
          style={{
            flex: 1,
            overflowY: "auto",
            background: "var(--background)",
            paddingBottom: "28px",
          }}
        >
          {children}
        </main>
        <StatusBar />
      </body>
    </html>
  );
}
