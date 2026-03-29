import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
  Field,
  FieldGroup,
  FieldLabel,
  Input,
  ScrollArea,
  Skeleton,
} from "@nqlib/nqui";
import { ArrowDown01Icon, Settings01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { toast } from "sonner";
import { fetchModels, streamChat } from "../api";
import { ChatLlmSettingsDialog } from "./ChatLlmSettingsDialog";
import type { ModelsResponse, RetrievalPayload } from "../types";

type ChatRole = "user" | "assistant";

type ChatLine = { role: ChatRole; text: string };

export type ChatThreadHandle = {
  openLlmSettings: () => void;
};

type ChatThreadProps = {
  sessionId: number;
  /** Tighter padding for the floating sheet */
  compact?: boolean;
};

function msToClock(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

export const ChatThread = forwardRef<ChatThreadHandle, ChatThreadProps>(function ChatThread(
  { sessionId, compact },
  ref
) {
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [chatSessionId, setChatSessionId] = useState<number | null>(null);
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [retrieval, setRetrieval] = useState<RetrievalPayload | null>(null);
  const [generating, setGenerating] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useImperativeHandle(ref, () => ({
    openLlmSettings: () => setSettingsOpen(true),
  }));

  useEffect(() => {
    void fetchModels()
      .then(setModels)
      .catch(() => {
        /* model bar stays empty */
      });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines, busy, retrieval, generating]);

  const send = async () => {
    const q = input.trim();
    if (!q || busy || !Number.isFinite(sessionId)) return;
    setInput("");
    setBusy(true);
    setRetrieval(null);
    setGenerating(false);
    setLines((prev) => [...prev, { role: "user", text: q }, { role: "assistant", text: "" }]);

    let assistant = "";

    try {
      for await (const ev of streamChat(sessionId, q, chatSessionId)) {
        if (ev.error) {
          const msg =
            typeof ev.message === "string"
              ? ev.message
              : "No relevant segments — index the session first.";
          toast.error(msg);
          setLines((prev) => {
            const n = [...prev];
            n[n.length - 1] = { role: "assistant", text: msg };
            return n;
          });
          break;
        }
        const rec = ev as Record<string, unknown>;
        if (rec.retrieval && typeof rec.retrieval === "object") {
          setRetrieval(rec.retrieval as RetrievalPayload);
        }
        if (typeof ev.token === "string") {
          if (ev.token.length) setGenerating(true);
          assistant += ev.token;
          setLines((prev) => {
            const n = [...prev];
            n[n.length - 1] = { role: "assistant", text: assistant };
            return n;
          });
        }
        if (ev.done === true && typeof ev.chat_session_id === "number") {
          setChatSessionId(ev.chat_session_id);
        }
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Chat failed");
      setLines((prev) => {
        const n = [...prev];
        if (n[n.length - 1]?.role === "assistant" && n[n.length - 1].text === "") {
          n[n.length - 1] = { role: "assistant", text: "(error)" };
        }
        return n;
      });
    } finally {
      setBusy(false);
      setGenerating(false);
    }
  };

  const pad = compact ? "p-3" : "p-4";
  const llmId = models?.llm.active_id ?? "…";

  return (
    <Card className="flex flex-1 min-h-0 flex-col border shadow-sm">
      <ChatLlmSettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        onSaved={() => {
          void fetchModels()
            .then(setModels)
            .catch(() => {
              /* ignore */
            });
        }}
      />
      <CardHeader className={`shrink-0 ${compact ? "py-2 space-y-2" : "py-3 space-y-2"}`}>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between min-w-0">
          {!compact && <CardTitle className="text-base">Ask about this session</CardTitle>}
          <div className="flex flex-wrap items-center gap-2 min-w-0 sm:ml-auto">
            {!compact && (
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="shrink-0 h-8 w-8"
                aria-label="LLM settings"
                onClick={() => setSettingsOpen(true)}
              >
                <HugeiconsIcon icon={Settings01Icon} className="size-4" />
              </Button>
            )}
            <span className="text-xs text-muted-foreground shrink-0">Active LLM</span>
            <Badge variant="secondary" className="max-w-[min(100%,20rem)] truncate font-mono text-xs" title={llmId}>
              {llmId}
            </Badge>
          </div>
        </div>
        <Collapsible defaultOpen={false} className="rounded-md border bg-muted/20">
          <CollapsibleTrigger className="group flex w-full items-center justify-between gap-2 px-2 py-1.5 text-left text-xs font-medium text-muted-foreground hover:bg-muted/40">
            <span>Model &amp; embedding details</span>
            <HugeiconsIcon
              icon={ArrowDown01Icon}
              className="size-3.5 shrink-0 transition-transform group-data-[state=open]:rotate-180"
            />
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="border-t px-2 py-2 space-y-1.5 text-xs text-muted-foreground">
              {models?.note && <p className="leading-snug">{models.note}</p>}
              <p>
                Embedding:{" "}
                <span className="font-mono text-foreground/90">{models?.embedding.active_id ?? "—"}</span>
              </p>
              <p className="leading-snug">
                Use the gear button to change the chat LLM and max tokens (saved in the database). RAG chunks
                appear below after you send a message.
              </p>
            </div>
          </CollapsibleContent>
        </Collapsible>
      </CardHeader>
      <CardContent className={`flex flex-1 min-h-0 flex-col gap-3 ${compact ? "pt-0" : ""}`}>
        <Collapsible defaultOpen={false} className="rounded-md border bg-background/80">
          <CollapsibleTrigger className="group flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm font-medium hover:bg-muted/50">
            <span>RAG chain — retrieved chunks</span>
            <HugeiconsIcon
              icon={ArrowDown01Icon}
              className="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180"
            />
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="border-t px-3 py-2 space-y-2 max-h-48 overflow-auto">
              {!retrieval && !busy && (
                <p className="text-xs text-muted-foreground">Send a message to see retrieved transcript chunks.</p>
              )}
              {busy && !retrieval && (
                <p className="text-xs text-muted-foreground">Embedding query and retrieving chunks…</p>
              )}
              {retrieval && (
                <>
                  <p className="text-xs text-muted-foreground">
                    Query: <span className="text-foreground">{retrieval.query}</span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Model for answer: <span className="font-mono">{retrieval.llm_model}</span>
                  </p>
                  <ul className="space-y-2">
                    {retrieval.chunks.map((c) => (
                      <li
                        key={c.id}
                        className="rounded border bg-muted/20 px-2 py-1.5 text-xs leading-relaxed"
                      >
                        <span className="text-muted-foreground font-mono">
                          #{c.chunk_index} · {msToClock(c.start_ms)}–{msToClock(c.end_ms)}
                        </span>
                        <p className="whitespace-pre-wrap break-words mt-0.5">{c.text}</p>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </CollapsibleContent>
        </Collapsible>

        {generating && (
          <p className="text-xs text-muted-foreground animate-pulse">Generating response…</p>
        )}

        <ScrollArea className={`flex-1 min-h-0 rounded-md border bg-muted/20 ${pad}`}>
          <div className="flex flex-col gap-4">
            {lines.length === 0 && !busy && (
              <p className="text-sm text-muted-foreground">
                Ask a question about the transcript. Ensure the session is indexed (reindex from the transcript
                screen if needed).
              </p>
            )}
            {lines.map((line, i) => (
              <div
                key={`${i}-${line.role}`}
                className={
                  line.role === "user"
                    ? "rounded-lg bg-primary/10 px-3 py-2 text-sm self-end max-w-[90%]"
                    : "rounded-lg bg-background border px-3 py-2 text-sm self-start max-w-[90%]"
                }
              >
                <span className="text-xs text-muted-foreground block mb-1">
                  {line.role === "user" ? "You" : "Assistant"}
                </span>
                <p className="whitespace-pre-wrap break-words">{line.text}</p>
              </div>
            ))}
            {busy && lines.length === 0 && (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-16 w-full" />
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>

        <FieldGroup className="gap-2">
          <Field>
            <FieldLabel htmlFor={`chat-q-${sessionId}`}>Message</FieldLabel>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
              <Input
                id={`chat-q-${sessionId}`}
                className="flex-1 min-w-0"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send();
                  }
                }}
                placeholder="What were the action items?"
                disabled={busy}
              />
              <Button type="button" onClick={() => void send()} disabled={busy || !input.trim()}>
                Send
              </Button>
            </div>
          </Field>
        </FieldGroup>
      </CardContent>
    </Card>
  );
});
