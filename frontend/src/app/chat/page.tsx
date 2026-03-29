"use client";

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useState } from "react";

export default function ChatPage() {
  const [transport] = useState(
    () => new DefaultChatTransport({ api: "/api/chat" })
  );
  const { messages, sendMessage, status, stop } = useChat({ transport });

  const handleSubmit = ({ text }: PromptInputMessage) => {
    if (!text.trim()) return;
    sendMessage({ text });
  };

  return (
    <div
      style={{
        height: "calc(100vh - 28px)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <Conversation>
        <ConversationContent className="max-w-3xl mx-auto w-full">
          {messages.length === 0 ? (
            <ConversationEmptyState
              title="Ask about your meetings"
              description="Chat with your local model about recordings, transcripts, or anything else."
            />
          ) : (
            messages.map((message) => (
              <Message from={message.role} key={message.id}>
                <MessageContent>
                  {message.parts
                    .filter((p) => p.type === "text")
                    .map((p, i) => (
                      <MessageResponse key={i}>{p.text}</MessageResponse>
                    ))}
                </MessageContent>
              </Message>
            ))
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <div
        style={{
          borderTop: "1px solid var(--border)",
          padding: "12px 24px 16px",
          background: "var(--background)",
          flexShrink: 0,
        }}
      >
        <div style={{ maxWidth: "768px", margin: "0 auto" }}>
          <PromptInput onSubmit={handleSubmit}>
            <PromptInputTextarea
              placeholder="Ask about your meetings…"
              disabled={status === "streaming" || status === "submitted"}
            />
            <PromptInputFooter>
              <PromptInputSubmit status={status} onStop={stop} />
            </PromptInputFooter>
          </PromptInput>
        </div>
      </div>
    </div>
  );
}
