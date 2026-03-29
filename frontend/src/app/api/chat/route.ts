import { createOpenAI } from "@ai-sdk/openai";
import { convertToModelMessages, streamText } from "ai";

const openai = createOpenAI({
  baseURL: process.env.MLX_BASE_URL ?? "http://localhost:8765/v1",
  apiKey: "not-needed",
});

const MODEL =
  process.env.MLX_MODEL_ID ?? "mlx-community/Qwen2.5-7B-Instruct-4bit";

export async function POST(request: Request) {
  const { messages } = await request.json();
  const result = streamText({
    model: openai.chat(MODEL),
    messages: await convertToModelMessages(messages),
  });
  return result.toUIMessageStreamResponse();
}
