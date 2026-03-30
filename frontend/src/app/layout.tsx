import type { Metadata } from "next";
import { Geist, Geist_Mono, Inter } from "next/font/google";
import Sidebar from "@/components/Sidebar";
import StatusBar from "@/components/StatusBar";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";
import { cn } from "@/lib/utils";

const inter = Inter({subsets:['latin'],variable:'--font-sans'});

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
      className={cn(geistSans.variable, geistMono.variable, "font-sans", inter.variable)}
    >
      <body
        style={{
          display: "flex",
          height: "100vh",
          overflow: "hidden",
          margin: 0,
        }}
      >
        <TooltipProvider>
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
        </TooltipProvider>
      </body>
    </html>
  );
}
