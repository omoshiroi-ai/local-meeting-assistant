import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
  ScrollArea,
  Separator,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  ToggleGroup,
  ToggleGroupItem,
} from "@nqlib/nqui";
import { Delete01Icon, FileViewIcon, Message01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { deleteSession, fetchHealth, fetchSessions, formatDuration } from "../api";
import type { HealthSnapshot, SessionOut } from "../types";

const FILTER_VALUES = ["all", "meeting", "work_process", "customer_service"] as const;
type FilterValue = (typeof FILTER_VALUES)[number];

function HealthBar({ health }: { health: HealthSnapshot | null }) {
  if (!health) {
    return (
      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-7 w-24" />
        <Skeleton className="h-7 w-24" />
        <Skeleton className="h-7 w-24" />
        <Skeleton className="h-7 w-24" />
      </div>
    );
  }
  const items = [
    ["Mic", health.microphone],
    ["Whisper", health.whisper],
    ["Embed", health.embedding],
    ["LLM", health.llm],
  ] as const;
  return (
    <div className="flex flex-wrap gap-2">
      {items.map(([label, s]) => (
        <Badge key={label} variant={s.ok ? "secondary" : "destructive"} className="text-xs font-normal">
          {label}: {s.ok ? "ok" : "issue"}
        </Badge>
      ))}
    </div>
  );
}

export function SessionsPage() {
  const [health, setHealth] = useState<HealthSnapshot | null>(null);
  const [sessions, setSessions] = useState<SessionOut[] | null>(null);
  const [filter, setFilter] = useState<FilterValue>("all");
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [h, list] = await Promise.all([
        fetchHealth(),
        fetchSessions(filter === "all" ? undefined : filter),
      ]);
      setHealth(h);
      setSessions(list);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  const onConfirmDelete = async () => {
    if (deleteId == null) return;
    try {
      await deleteSession(deleteId);
      toast.success("Session deleted");
      setDeleteId(null);
      void load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  };

  return (
    <div className="flex flex-1 min-h-0 flex-col gap-4 p-6">
      <div className="flex flex-col gap-3 min-w-0">
        <div>
          <h1 className="text-xl font-semibold leading-none">Recordings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Browse sessions, open transcripts, or chat (recording still uses the terminal app).
          </p>
        </div>
        <HealthBar health={health} />
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <span className="text-sm text-muted-foreground">Session type</span>
          <ToggleGroup
            type="single"
            value={filter}
            onValueChange={(v) => v && setFilter(v as FilterValue)}
            variant="outline"
            size="sm"
            className="flex-wrap"
          >
            <ToggleGroupItem value="all">All</ToggleGroupItem>
            <ToggleGroupItem value="meeting">Meeting</ToggleGroupItem>
            <ToggleGroupItem value="work_process">Work</ToggleGroupItem>
            <ToggleGroupItem value="customer_service">Support</ToggleGroupItem>
          </ToggleGroup>
        </div>
      </div>

      <Separator />

      <Card className="flex flex-1 min-h-0 flex-col border shadow-sm">
        <CardHeader className="shrink-0 py-3">
          <CardTitle className="text-base">Sessions</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 p-0">
          {loading ? (
            <div className="flex flex-col gap-2 p-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : !sessions?.length ? (
            <div className="p-6">
              <Empty className="border border-dashed rounded-lg">
                <EmptyHeader>
                  <EmptyTitle>No sessions yet</EmptyTitle>
                  <EmptyDescription>
                    Start a recording with{" "}
                    <code className="rounded bg-muted px-1 py-0.5 text-xs">uv run meeting-assistant</code>{" "}
                    in the terminal.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            </div>
          ) : (
            <ScrollArea className="h-[min(560px,calc(100vh-16rem))]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-0">Title</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead className="text-right w-[200px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="min-w-0 max-w-[240px] font-medium truncate">
                        {s.title || "Untitled"}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs font-normal">
                          {s.session_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground whitespace-nowrap">
                        {s.started_at.slice(0, 10)}
                      </TableCell>
                      <TableCell className="text-muted-foreground whitespace-nowrap">
                        {s.ended_at ? formatDuration(s.duration_secs) : "live…"}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex flex-wrap justify-end gap-2">
                          <Button variant="outline" size="sm" asChild>
                            <Link to={`/sessions/${s.id}/transcript`}>
                              <HugeiconsIcon icon={FileViewIcon} data-icon="inline-start" />
                              Transcript
                            </Link>
                          </Button>
                          <Button variant="outline" size="sm" asChild>
                            <Link to={`/sessions/${s.id}/chat`}>
                              <HugeiconsIcon icon={Message01Icon} data-icon="inline-start" />
                              Chat
                            </Link>
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => setDeleteId(s.id)}>
                            <HugeiconsIcon icon={Delete01Icon} data-icon="inline-start" />
                            Delete
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={deleteId != null} onOpenChange={(o) => !o && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete session?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes the session and its transcript from local storage. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel variant="outline" size="default">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction variant="default" size="default" onClick={() => void onConfirmDelete()}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
