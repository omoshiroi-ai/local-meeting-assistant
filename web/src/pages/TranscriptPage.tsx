import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
  ScrollArea,
  Separator,
  Skeleton,
} from "@nqlib/nqui";
import { ArrowDown01Icon, ArrowLeft01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { fetchSegments, postReindex, summarizeSession } from "../api";
import { speechSupported, speakText, stopSpeaking } from "../lib/speech";
import type { SegmentOut } from "../types";

function msToClock(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

export function TranscriptPage() {
  const { id } = useParams<{ id: string }>();
  const sessionId = Number(id);
  const [segments, setSegments] = useState<SegmentOut[] | null>(null);
  const [reindexing, setReindexing] = useState(false);
  const [summary, setSummary] = useState<string | null>(null);
  const [summaryModel, setSummaryModel] = useState<string | null>(null);
  const [summarizing, setSummarizing] = useState(false);

  useEffect(() => {
    if (!Number.isFinite(sessionId)) return;
    void (async () => {
      try {
        const segs = await fetchSegments(sessionId);
        setSegments(segs);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to load transcript");
      }
    })();
  }, [sessionId]);

  const onReindex = async () => {
    setReindexing(true);
    try {
      const r = await postReindex(sessionId);
      toast.success(`Indexed ${r.indexed_chunks} chunks`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Reindex failed");
    } finally {
      setReindexing(false);
    }
  };

  const onSummarize = async () => {
    setSummarizing(true);
    try {
      const r = await summarizeSession(sessionId);
      setSummary(r.summary);
      setSummaryModel(r.llm_model);
      toast.success("Summary ready");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Summarize failed");
    } finally {
      setSummarizing(false);
    }
  };

  if (!Number.isFinite(sessionId)) {
    return <p className="p-6 text-sm text-muted-foreground">Invalid session.</p>;
  }

  return (
    <div className="flex flex-1 min-h-0 flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="outline" size="sm" asChild>
          <Link to="/">
            <HugeiconsIcon icon={ArrowLeft01Icon} data-icon="inline-start" />
            Back
          </Link>
        </Button>
        <Separator orientation="vertical" className="h-6 hidden sm:block" />
        <h1 className="text-xl font-semibold">Transcript</h1>
        <div className="flex-1" />
        <Button variant="secondary" size="sm" disabled={reindexing} onClick={() => void onReindex()}>
          {reindexing ? "Reindexing…" : "Reindex for chat"}
        </Button>
        <Button size="sm" asChild>
          <Link to={`/sessions/${sessionId}/chat`}>Open chat</Link>
        </Button>
      </div>

      <Collapsible defaultOpen className="rounded-lg border bg-muted/15">
        <CollapsibleTrigger className="group flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm font-medium">
          <span>AI summary &amp; voice (local LLM + browser TTS)</span>
          <HugeiconsIcon
            icon={ArrowDown01Icon}
            className="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180"
          />
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="border-t px-4 py-3 space-y-3 text-sm">
            <p className="text-xs text-muted-foreground leading-relaxed">
              Summarization uses the same local MLX model as chat. Speech uses your browser&apos;s{" "}
              <code className="text-xs bg-muted px-1 rounded">speechSynthesis</code> (macOS: System Settings →
              Accessibility → Spoken Content; pick a voice there).
            </p>
            <div className="flex flex-wrap gap-2">
              <Button type="button" size="sm" disabled={summarizing} onClick={() => void onSummarize()}>
                {summarizing ? "Summarizing…" : "Generate summary"}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={!summary || !speechSupported()}
                onClick={() => summary && speakText(summary)}
              >
                Speak summary
              </Button>
              <Button type="button" size="sm" variant="outline" onClick={() => stopSpeaking()}>
                Stop speaking
              </Button>
            </div>
            {summaryModel && (
              <p className="text-xs text-muted-foreground font-mono">Model: {summaryModel}</p>
            )}
            {summary && (
              <div className="rounded-md border bg-background p-3 text-sm whitespace-pre-wrap break-words max-h-64 overflow-auto">
                {summary}
              </div>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>

      <Card className="flex flex-1 min-h-0 flex-col border shadow-sm">
        <CardHeader className="shrink-0 py-3">
          <CardTitle className="text-base">Segments</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 p-0">
          {segments === null ? (
            <div className="flex flex-col gap-2 p-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : segments.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">No transcript segments yet.</p>
          ) : (
            <ScrollArea className="h-[min(560px,calc(100vh-12rem))]">
              <ul className="flex flex-col gap-3 p-4">
                {segments.map((s) => (
                  <li key={s.id} className="flex flex-col gap-1 border-b border-border/60 pb-3 last:border-0">
                    <span className="text-xs text-muted-foreground font-mono">
                      {msToClock(s.start_ms)} – {msToClock(s.end_ms)}
                    </span>
                    <p className="text-sm text-foreground whitespace-pre-wrap break-words">{s.text}</p>
                  </li>
                ))}
              </ul>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
