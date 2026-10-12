import { useState, useRef, useEffect, useCallback } from "react";
import "./App.css";

function linkifyPaths(text) {
  const parts = [];
  const regex = /(~\/[^\s,'")\]]+|\/Users\/[^\s,'")\]]+|\/[a-zA-Z][^\s,'")\]]*\.(pdf|txt|md|py|js|json|csv|docx|xlsx|png|jpg))/g;
  let last = 0, m;
  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    parts.push(<PathLink key={m.index} path={m[0]} />);
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function PathLink({ path }) {
  const [copied, setCopied] = useState(false);
  const copy = () => { navigator.clipboard.writeText(path); setCopied(true); setTimeout(() => setCopied(false), 1500); };
  return (
    <span className="path-link" onClick={copy} title="Click to copy path">
      {path}
      <span className="path-badge">{copied ? "copied!" : "copy path"}</span>
    </span>
  );
}

function CopyCmd({ cmd }) {
  const [copied, setCopied] = useState(false);
  const copy = () => { navigator.clipboard.writeText(cmd); setCopied(true); setTimeout(() => setCopied(false), 1500); };
  return (
    <div className="install-cmd">
      <code>{cmd}</code>
      <button className="copy-btn" onClick={copy}>{copied ? "✓" : "copy"}</button>
    </div>
  );
}

function ToolCall({ name, result }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="tool-call" onClick={() => setOpen(o => !o)}>
      <span className="tool-icon">⚙</span>
      <span className="tool-name">{name}</span>
      <span className="tool-chevron">{open ? "▲" : "▼"}</span>
      {open && result && <div className="tool-result">{result}</div>}
    </div>
  );
}

function Message({ role, content, toolCalls, onEdit }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(content);
  const save = () => { onEdit(draft); setEditing(false); };
  return (
    <div className={`message ${role}`}>
      {toolCalls && toolCalls.length > 0 && (
        <div className="tool-calls">
          {toolCalls.map((tc, i) => <ToolCall key={i} {...tc} />)}
        </div>
      )}
      {content !== undefined && (
        <div className="bubble-wrap">
          {editing ? (
            <div className="edit-wrap">
              <textarea className="edit-input" value={draft} onChange={e => setDraft(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); save(); } }} autoFocus />
              <div className="edit-actions">
                <button className="edit-save" onClick={save}>Save</button>
                <button className="edit-cancel" onClick={() => setEditing(false)}>Cancel</button>
              </div>
            </div>
          ) : (
            <div className="bubble" onDoubleClick={() => role === "user" && setEditing(true)}>
              <p style={{ whiteSpace: "pre-wrap" }}>
                {role === "assistant" ? linkifyPaths(content) : content}
              </p>
              {role === "user" && (
                <button className="edit-btn" onClick={() => setEditing(true)} title="Edit">✎</button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function LocalBanner() {
  const [open, setOpen] = useState(false);
  return (
    <div className="local-banner">
      <button className="local-toggle" onClick={() => setOpen(o => !o)}>
        <span>💻</span> Run PocketAI locally in your terminal
        <span className="local-chevron">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="local-steps">
          <div className="install-option">
            <p className="install-label">🆓 Free — Llama 3 (no API key needed)</p>
            <CopyCmd cmd="curl -fsSL https://raw.githubusercontent.com/Jemimahosei/PocketAi/main/install.sh | bash" />
          </div>
          <div className="install-option">
            <p className="install-label">⚡ Smarter — Claude (requires Anthropic API key)</p>
            <CopyCmd cmd="curl -fsSL https://raw.githubusercontent.com/Jemimahosei/PocketAi/main/install-claude.sh | bash" />
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [agentName, setAgentName] = useState("PocketAI");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const abortRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    fetch("http://localhost:5001/agent-name").then(r => r.json()).then(d => setAgentName(d.name)).catch(() => {});
  }, []);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const stopGeneration = () => { abortRef.current?.abort(); setLoading(false); };

  const toggleMic = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert("Speech recognition not supported in this browser."); return; }
    if (listening) { recognitionRef.current?.stop(); setListening(false); return; }
    const rec = new SR();
    rec.continuous = false; rec.interimResults = false; rec.lang = "en-US";
    rec.onresult = e => setInput(prev => prev + (prev ? " " : "") + e.results[0][0].transcript);
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recognitionRef.current = rec; rec.start(); setListening(true);
  };

  const sendMessage = useCallback(async (overrideText) => {
    const text = (overrideText ?? input).trim();
    if (!text || loading) return;
    const history = messages.filter(m => m.role === "user" || m.role === "assistant").map(m => ({ role: m.role, content: m.content }));
    setMessages(prev => [...prev, { role: "user", content: text }]);
    setInput(""); setLoading(true);
    let assistantContent = "", toolCalls = [];
    setMessages(prev => [...prev, { role: "assistant", content: "", toolCalls: [] }]);
    const controller = new AbortController(); abortRef.current = controller;
    try {
      const res = await fetch("http://localhost:5001/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history }), signal: controller.signal,
      });
      const reader = res.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n"); buffer = parts.pop();
        for (const part of parts) {
          const lines = part.split("\n"); let eventType = "", dataStr = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) eventType = line.slice(7).trim();
            if (line.startsWith("data: ")) dataStr = line.slice(6).trim();
          }
          if (!dataStr) continue;
          const data = JSON.parse(dataStr);
          if (eventType === "token") {
            assistantContent += data.text;
            setMessages(prev => { const next = [...prev]; next[next.length - 1] = { role: "assistant", content: assistantContent, toolCalls: [...toolCalls] }; return next; });
          } else if (eventType === "tool_call") {
            toolCalls.push({ name: data.name, result: null });
            setMessages(prev => { const next = [...prev]; next[next.length - 1] = { role: "assistant", content: assistantContent, toolCalls: [...toolCalls] }; return next; });
          } else if (eventType === "tool_result") {
            const idx = toolCalls.findLastIndex(t => t.result === null);
            if (idx >= 0) toolCalls[idx].result = data.result?.slice(0, 300);
            setMessages(prev => { const next = [...prev]; next[next.length - 1] = { role: "assistant", content: assistantContent, toolCalls: [...toolCalls] }; return next; });
          }
        }
      }
    } catch (e) {
      if (e.name !== "AbortError") {
        setMessages(prev => { const next = [...prev]; next[next.length - 1] = { role: "assistant", content: "Connection error — is the server running?", toolCalls: [] }; return next; });
      }
    }
    setLoading(false); inputRef.current?.focus();
  }, [input, loading, messages]);

  const handleEdit = (msgIndex, newText) => { setMessages(messages.slice(0, msgIndex)); sendMessage(newText); };

  return (
    <div className="app">
      <header className="header">
        <div className="header-left"><span className="logo">✦</span><span className="agent-name">{agentName}</span></div>
        <span className="badge">PocketAI</span>
      </header>
      <LocalBanner />
      <main className="chat-area">
        {messages.length === 0 && (
          <div className="empty-state">
            <p className="empty-title">What can I help you with?</p>
            <div className="suggestions">
              {["Search the web", "Read a file", "List my directory"].map(s => (
                <button key={s} className="suggestion" onClick={() => setInput(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => <Message key={i} {...m} onEdit={newText => handleEdit(i, newText)} />)}
        {loading && <div className="message assistant"><div className="bubble typing"><span /><span /><span /></div></div>}
        <div ref={bottomRef} />
      </main>
      <footer className="input-area">
        <button className={`mic-btn ${listening ? "listening" : ""}`} onClick={toggleMic} title={listening ? "Stop" : "Voice input"}>
          {listening ? "⏹" : "🎤"}
        </button>
        <textarea ref={inputRef} className="input" value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
          placeholder={`Message ${agentName}…`} rows={1} />
        {loading
          ? <button className="stop-btn" onClick={stopGeneration}>■</button>
          : <button className="send-btn" onClick={() => sendMessage()} disabled={!input.trim()}>↑</button>}
      </footer>
    </div>
  );
}
