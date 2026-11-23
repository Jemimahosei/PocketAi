// Talks to the local PocketAI server (server/app.py, port 5001).
// Same contract as the previous frontend: GET /agent-name, and
// POST /chat streaming SSE events: token, tool_call, tool_result, done.
import { SERVER_URL } from "../data/samples";

export async function fetchAgentName() {
  const r = await fetch(`${SERVER_URL}/agent-name`);
  if (!r.ok) throw new Error("no server");
  const d = await r.json();
  return d.name;
}

// handlers: onToken(text), onToolCall({name, input}), onToolResult(resultText)
export async function streamChat({ message, history, signal, onToken, onToolCall, onToolResult }) {
  const res = await fetch(`${SERVER_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error("chat failed");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop();
    for (const part of parts) {
      let eventType = "";
      let dataStr = "";
      for (const line of part.split("\n")) {
        if (line.startsWith("event: ")) eventType = line.slice(7).trim();
        if (line.startsWith("data: ")) dataStr = line.slice(6).trim();
      }
      if (!dataStr) continue;
      let data;
      try {
        data = JSON.parse(dataStr);
      } catch {
        continue;
      }
      if (eventType === "token") onToken?.(data.text || "");
      else if (eventType === "tool_call") onToolCall?.({ name: data.name, input: data.input || {} });
      else if (eventType === "tool_result") onToolResult?.(data.result || "");
    }
  }
}

export function toolArg(input) {
  if (!input) return "";
  return input.path || input.query || "";
}
