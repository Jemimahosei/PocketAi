// Talks to the local PocketAI server (server/app.py, port 5001).
// Contract: GET /agent-name, and POST /chat streaming SSE events:
// token, tool_call, tool_result, done, error.
//
// The /chat body now also carries "model" ("llama" | "claude") — the
// install-tab choice the app keeps in localStorage as
// `pocketai-model` — so the server serves the backend the user picked
// instead of always using Claude.
import { SERVER_URL } from "../data/samples";

export async function fetchAgentName() {
  const r = await fetch(`${SERVER_URL}/agent-name`);
  if (!r.ok) throw new Error("no server");
  const d = await r.json();
  return d.name;
}

// Full /agent-name payload ({name, default_backend, backends}) for
// anything that wants to show which model the server can serve.
export async function fetchServerInfo() {
  const r = await fetch(`${SERVER_URL}/agent-name`);
  if (!r.ok) throw new Error("no server");
  return r.json();
}

// handlers: onToken(text), onToolCall({name, input}), onToolResult(resultText)
// Throws when the server answers non-200 (e.g. 503 when the chosen
// backend isn't running) or when the stream reports an error before
// producing anything — the chat page turns that into its existing
// "PocketAI is not running on this computer" state.
export async function streamChat({ message, history, model, signal, onToken, onToolCall, onToolResult }) {
  const res = await fetch(`${SERVER_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, model }),
    signal,
  });
  if (!res.ok || !res.body) {
    let detail = "";
    try {
      detail = (await res.json())?.error || "";
    } catch {
      /* non-JSON error body — nothing more to learn */
    }
    throw new Error(detail || "chat failed");
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let sawData = false;
  let streamError = "";
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
      if (eventType === "token") {
        sawData = true;
        onToken?.(data.text || "");
      } else if (eventType === "tool_call") {
        sawData = true;
        onToolCall?.({ name: data.name, input: data.input || {} });
      } else if (eventType === "tool_result") {
        sawData = true;
        onToolResult?.(data.result || "");
      } else if (eventType === "error") {
        streamError = data.message || "Something went wrong";
      }
    }
  }
  // An error that arrives before any answer content means the backend
  // failed outright (e.g. Ollama stopped mid-request) — surface it the
  // same way as a dead server. Errors after partial content are left
  // alone so the user keeps what already streamed in.
  if (streamError && !sawData) throw new Error(streamError);
}

export function toolArg(input) {
  if (!input) return "";
  return input.path || input.query || "";
}
