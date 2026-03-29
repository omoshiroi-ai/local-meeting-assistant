import {
  NquiLogo,
  Separator,
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@nqlib/nqui";
import { Home01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import type { CSSProperties } from "react";
import { Link, Route, Routes } from "react-router-dom";
import { FloatingChatPanel } from "./components/FloatingChatPanel";
import { ChatPage } from "./pages/ChatPage";
import { SessionsPage } from "./pages/SessionsPage";
import { TranscriptPage } from "./pages/TranscriptPage";

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider
      defaultOpen={false}
      style={
        {
          "--sidebar-width": "16rem",
        } as CSSProperties
      }
    >
      <Sidebar>
        <SidebarHeader>
          <div className="flex items-center gap-2 px-2 py-4 min-w-0">
            <NquiLogo className="size-8 shrink-0" />
            <div className="flex flex-col min-w-0">
              <span className="font-semibold text-sm truncate">Local Assistant</span>
              <span className="text-xs text-muted-foreground truncate">Recordings</span>
            </div>
          </div>
        </SidebarHeader>
        <SidebarContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton asChild>
                <Link to="/">
                  <HugeiconsIcon icon={Home01Icon} data-icon="inline-start" />
                  <span>Sessions</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarContent>
      </Sidebar>
      <SidebarInset className="flex flex-col min-h-screen min-w-0">
        <header className="flex h-12 items-center gap-2 border-b px-4 shrink-0 bg-background/95">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="h-4" />
          <span className="text-sm font-medium">Local Meeting Assistant</span>
        </header>
        <main className="flex-1 min-h-0 flex flex-col min-w-0">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<SessionsPage />} />
        <Route path="/sessions/:id/transcript" element={<TranscriptPage />} />
        <Route path="/sessions/:id/chat" element={<ChatPage />} />
      </Routes>
      <FloatingChatPanel />
    </Layout>
  );
}
