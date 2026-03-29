import { Button, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Sheet, SheetContent, SheetHeader, SheetTitle } from "@nqlib/nqui";
import { BubbleChatIcon, Settings01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { toast } from "sonner";
import { fetchSessions } from "../api";
import type { SessionOut } from "../types";
import { ChatThread, type ChatThreadHandle } from "./ChatThread";

export function FloatingChatPanel() {
  const loc = useLocation();
  const routeMatch = loc.pathname.match(/\/sessions\/(\d+)\/(?:chat|transcript)/);
  const routeSessionId = routeMatch ? Number(routeMatch[1]) : null;

  const [open, setOpen] = useState(false);
  const [sessions, setSessions] = useState<SessionOut[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const chatThreadRef = useRef<ChatThreadHandle>(null);

  useEffect(() => {
    if (routeSessionId != null) {
      setSessionId(routeSessionId);
    }
  }, [routeSessionId]);

  useEffect(() => {
    if (!open) return;
    void (async () => {
      try {
        const list = await fetchSessions();
        setSessions(list);
        setSessionId((cur) => {
          if (cur != null && list.some((s) => s.id === cur)) return cur;
          if (routeSessionId != null && list.some((s) => s.id === routeSessionId)) return routeSessionId;
          return list[0]?.id ?? null;
        });
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to load sessions");
      }
    })();
  }, [open, routeSessionId]);

  return (
    <>
      <Button
        type="button"
        size="lg"
        className="fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full shadow-lg p-0"
        onClick={() => setOpen(true)}
        aria-label="Open chat"
      >
        <HugeiconsIcon icon={BubbleChatIcon} className="size-6" />
      </Button>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-lg">
          <SheetHeader className="border-b px-4 py-3 shrink-0 text-left space-y-0">
            <div className="flex items-center gap-2 min-w-0">
              <SheetTitle className="shrink-0">Chat</SheetTitle>
              <Select
                value={sessionId != null ? String(sessionId) : ""}
                onValueChange={(v) => setSessionId(Number(v))}
                disabled={sessions.length === 0}
              >
                <SelectTrigger
                  id="float-session"
                  className="h-9 min-w-0 max-w-48 shrink text-left font-normal [&>span]:truncate"
                >
                  <SelectValue placeholder={sessions.length ? "Session" : "No sessions"} />
                </SelectTrigger>
                <SelectContent>
                  {sessions.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.title || `Session ${s.id}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="shrink-0 h-8 w-8"
                aria-label="LLM settings"
                disabled={sessionId == null || !Number.isFinite(sessionId)}
                onClick={() => chatThreadRef.current?.openLlmSettings()}
              >
                <HugeiconsIcon icon={Settings01Icon} className="size-4" />
              </Button>
            </div>
          </SheetHeader>
          <div className="flex flex-1 min-h-0 flex-col overflow-hidden p-3">
            {sessionId != null && Number.isFinite(sessionId) ? (
              <ChatThread ref={chatThreadRef} sessionId={sessionId} compact />
            ) : (
              <p className="text-sm text-muted-foreground p-2">Create or select a session to chat.</p>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
