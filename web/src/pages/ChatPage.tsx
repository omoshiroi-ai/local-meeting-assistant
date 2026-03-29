import { Button, Separator } from "@nqlib/nqui";
import { ArrowLeft01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { Link, useParams } from "react-router-dom";
import { ChatThread } from "../components/ChatThread";

export function ChatPage() {
  const { id } = useParams<{ id: string }>();
  const sessionId = Number(id);

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
        <h1 className="text-xl font-semibold">Chat</h1>
        <div className="flex-1" />
        <Button variant="outline" size="sm" asChild>
          <Link to={`/sessions/${sessionId}/transcript`}>Transcript</Link>
        </Button>
      </div>

      <ChatThread sessionId={sessionId} />
    </div>
  );
}
