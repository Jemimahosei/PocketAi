import { useCallback, useEffect, useRef, useState } from "react";
import { RUNS, INSTALLS } from "../data/samples";
import { streamChat, toolArg } from "../lib/chatApi";
import { Logo, MicIcon, SendIcon, ToolStep, AnswerText } from "../components/ui";

export default function Chat({ onBack, modelId, onPickModel, serverInfo, serverDown }) {
  const model = INSTALLS.find((i) => i.id === modelId) || INSTALLS[0];
  // Voice input uses the browser's Web Speech API (Chrome and Safari
  // only). Where it doesn't exist, the mic button is not shown at
  // all instead of sitting there dead.
  const micSupported = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  const agentName = serverInfo?.name || "PocketAI";
  const hosted = serverInfo?.environment === "hosted";
  const fileTools = serverInfo?.file_tools !== false;
  const conn = serverDown ? "offline" : serverInfo ? "live" : "checking";

  const [messages, setMessages] = useState(null); // null = no conversation yet
  const [showOffline, setShowOffline] = useState(false);
  const [draft, setDraft] = useState("");
  const [copyNote, setCopyNote] = useState("");
  const [copiedPath, setCopiedPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [editingIdx, setEditingIdx] = useState(null);
  const [editDraft, setEditDraft] = useState("");
  const abortRef = useRef(null);
  const recogRef = useRef(null);
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (serverDown) setShowOffline(true);
  }, [serverDown]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, showOffline]);

  const noteCopy = useCallback((path) => {
    setCopiedPath(path);
    setCopyNote(`Copied ${path}`);
  }, []);

  // ── Live sending (SSE) ────────────────────────────────────────────────
  const sendLive = useCallback(
    async (text, baseMessages) => {
      const history = baseMessages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({ role: m.role, content: m.content }));
      let next = [...baseMessages, { role: "user", content: text }, { role: "assistant", content: "", toolCalls: [] }];
      setMessages(next);
      setLoading(true);
      let content = "";
      let toolCalls = [];
      const controller = new AbortController();
      abortRef.current = controller;
      const patch = () => {
        next = [...next];
        next[next.length - 1] = { role: "assistant", content, toolCalls: [...toolCalls] };
        setMessages(next);
      };
      try {
        await streamChat({
          message: text,
          model: modelId,
          history,
          signal: controller.signal,
          onToken: (t) => {
            content += t;
            patch();
          },
          onToolCall: (tc) => {
            toolCalls.push({ name: tc.name, arg: toolArg(tc.input), result: null, open: false });
            patch();
          },
          onToolResult: (result) => {
            const idx = toolCalls.findLastIndex((t) => t.result === null);
            if (idx >= 0) toolCalls[idx].result = result.slice(0, 300);
            patch();
          },
        });
      } catch (e) {
        if (e.name === "AbortError") {
          // Stopped by the user — keep whatever streamed in.
        } else if (e.serverMessage) {
          // The server explained the problem (key rejected, model not
          // running, …). Show it in the thread; the conversation and
          // the connection both survive.
          const base = content || toolCalls.length ? next : next.slice(0, -1);
          setMessages([...base, { role: "error", content: e.message }]);
        } else if (content || toolCalls.length || baseMessages.length) {
          // The server died mid-conversation — keep the thread and say so.
          setMessages([...next, { role: "error", content: "The server stopped answering. Your earlier messages are still here." }]);
        } else {
          // Nothing ever arrived: the server is not there at all.
          setMessages(null);
          setShowOffline(true);
        }
      }
      setLoading(false);
      inputRef.current?.focus();
    },
    [modelId]
  );

  const submit = (text) => {
    const t = (text ?? draft).trim();
    if (!t || loading) return;
    setDraft("");
    setShowOffline(false);
    sendLive(t, messages || []);
  };

  const stop = () => {
    abortRef.current?.abort();
    setLoading(false);
  };

  const toggleMic = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      alert("Speech recognition not supported in this browser.");
      return;
    }
    if (listening) {
      recogRef.current?.stop();
      setListening(false);
      return;
    }
    const rec = new SR();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = "en-US";
    rec.onresult = (e) => setDraft((prev) => prev + (prev ? " " : "") + e.results[0][0].transcript);
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recogRef.current = rec;
    rec.start();
    setListening(true);
  };

  // ── Files it opened (sidebar) ─────────────────────────────────────────
  const files = [];
  if (messages) {
    for (const m of messages) {
      for (const tc of m.toolCalls || []) {
        if (tc.arg && (tc.name === "read_file" || tc.name === "read_pdf" || tc.name === "list_directory")) {
          if (!files.some((f) => f.name === tc.arg)) {
            files.push({
              name: tc.arg,
              hint: tc.name === "list_directory" ? "Folder" : tc.name === "read_pdf" ? "PDF" : "File",
            });
          }
        }
      }
    }
  }

  const copyFile = (name) => {
    try {
      navigator.clipboard.writeText(name);
    } catch {
      /* ignore */
    }
    noteCopy(name);
  };

  return (
    <div className="page chat-page">
      <div className="chat-topbar">
        <span className="phone-only topbar-brand">
          <Logo size={26} />
          {agentName}
        </span>
        <button type="button" className="text-link back-link phone-hide" onClick={onBack}>
          Back to the home page
        </button>
        <button type="button" className="text-link back-link phone-only" onClick={onBack}>
          Back
        </button>
        {conn === "live" && (
          <span>
            {hosted
              ? `Connected to the hosted ${agentName} demo — file access is off on the website.`
              : `Connected to ${agentName} on this computer.`}
          </span>
        )}
        {conn === "offline" && <span>Not connected.</span>}
        <span className="phone-only mono model-badge">
          {model.modelLabel}
          {model.id === "llama" ? ", local" : ", cloud"}
        </span>
      </div>

      <div className="chat-layout">
        <aside className="chat-side phone-hide">
          <div className="side-brand">
            <Logo size={32} />
            {agentName}
          </div>
          <div>
            <div className="folder-tab-label">Files it opened</div>
            <div className="folder-box">
              {files.length === 0 && (
                <p className="folder-empty">
                  {fileTools
                    ? "Nothing yet. Each file PocketAI opens in this chat is filed here, and you can copy its path."
                    : "File access is off on this hosted demo. In the local install, each file PocketAI opens is filed here."}
                </p>
              )}
              {files.map((f) => (
                <button key={f.name} type="button" className="file-btn mono" onClick={() => copyFile(f.name)}>
                  {f.name}
                  <span className="file-hint">{copiedPath === f.name ? "Path copied" : f.hint}</span>
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="folder-tab-label">Model</div>
            <div role="group" aria-label="Choose the model" className="state-group">
              {INSTALLS.map((i) => {
                const avail = serverInfo?.backends?.[i.id]?.available;
                return (
                  <button
                    key={i.id}
                    type="button"
                    className="state-btn"
                    aria-pressed={modelId === i.id}
                    disabled={avail === false}
                    title={
                      avail === false
                        ? i.id === "llama"
                          ? hosted
                            ? "Llama runs on your own computer — it isn't part of the hosted demo"
                            : "Ollama is not running, so Llama can't answer right now"
                          : "Claude is not set up on this server"
                        : i.name
                    }
                    style={{
                      borderColor: modelId === i.id ? "#1c2630" : "#b6bdc6",
                      background: modelId === i.id ? "#ecd9a0" : "#fdfdfc",
                      opacity: avail === false ? 0.5 : 1,
                    }}
                    onClick={() => onPickModel?.(i.id)}
                  >
                    {i.modelLabel}
                  </button>
                );
              })}
            </div>
            <div className="model-note">
              Model <span className="mono">{model.modelLabel}</span>
              {model.id === "llama" ? ", running on this computer. Nothing is sent anywhere." : ", via Anthropic."}
            </div>
            {serverInfo?.backends?.llama?.available === false && (
              <p className="model-note">
                {hosted
                  ? "Llama runs on your own computer, so it isn't part of this hosted demo — the free local install includes it."
                  : "Llama isn't answering right now — start Ollama to use it."}
              </p>
            )}
            {serverInfo?.backends?.claude?.available === false && (
              <p className="model-note">Claude needs an API key before it can answer.</p>
            )}
          </div>
        </aside>

        <section className="chat-main">
          <div className="chat-card">
            <div className="thread" aria-live="polite" ref={scrollRef}>
              {messages === null && !showOffline && (
                <div className="empty-state">
                  <h1>What should I look up?</h1>
                  <p>
                    {hosted
                      ? "Ask me anything, or ask about the web. This hosted demo can't open files on your computer — file access works in the free local install. The demo also sleeps when idle, so the first reply can take up to a minute to wake it."
                      : "Ask about a file, a folder, or anything on the web. I will say which tool I am using."}
                  </p>
                  <div className="chips">
                    {RUNS.map((x) => (
                      <button key={x.key} type="button" className="chip" onClick={() => submit(x.ask)}>
                        {x.ask}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages === null && showOffline && (
                <div className="offline-card">
                  {hosted ? (
                    <>
                      <h1>The hosted PocketAI demo isn't responding</h1>
                      <p>It may be waking up. Wait a few seconds, then send your message again.</p>
                    </>
                  ) : (
                    <>
                      <h1>PocketAI is not running on this computer</h1>
                      <p>
                        This page talks to a small server on your own machine, and it did not answer. Start it, then
                        send your message again.
                      </p>
                      <code className="mono offline-cmd">python3 server/app.py</code>
                      <p className="offline-more">Have not installed it yet? The home page has the one command install.</p>
                    </>
                  )}
                </div>
              )}

              {messages !== null &&
                messages.map((m, i) =>
                  m.role === "error" ? (
                    <div key={i} className="unknown-note">
                      {m.content}
                    </div>
                  ) : m.role === "user" ? (
                    <div key={i} className="user-row">
                      {editingIdx === i ? (
                        <div className="edit-wrap">
                          <textarea
                            className="edit-input"
                            value={editDraft}
                            onChange={(e) => setEditDraft(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                const base = messages.slice(0, i);
                                setEditingIdx(null);
                                sendLive(editDraft, base);
                              }
                            }}
                            autoFocus
                          />
                          <div className="edit-actions">
                            <button
                              type="button"
                              className="btn-dark"
                              onClick={() => {
                                const base = messages.slice(0, i);
                                setEditingIdx(null);
                                sendLive(editDraft, base);
                              }}
                            >
                              Save and resend
                            </button>
                            <button type="button" className="btn-outline" onClick={() => setEditingIdx(null)}>
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="bubble user">{m.content}</div>
                          <button
                            type="button"
                            className="edit-link"
                            onClick={() => {
                              setEditingIdx(i);
                              setEditDraft(m.content);
                            }}
                          >
                            Edit and resend
                          </button>
                        </>
                      )}
                    </div>
                  ) : (
                    <div key={i} className="answer-block">
                      {(m.toolCalls || []).map((tc, j) => (
                        <ToolStep
                          key={j}
                          tool={tc.name}
                          arg={tc.arg}
                          note={tc.result ? "done" : "looking"}
                          stamp={tc.name === "read_pdf" || tc.name === "read_file"}
                          expandable={!!tc.result}
                          expanded={tc.open}
                          result={tc.result}
                          onToggle={() => {
                            const copy = [...messages];
                            const tcs = [...copy[i].toolCalls];
                            tcs[j] = { ...tcs[j], open: !tcs[j].open };
                            copy[i] = { ...copy[i], toolCalls: tcs };
                            setMessages(copy);
                          }}
                        />
                      ))}
                      {m.content ? (
                        <div className="bubble assistant answer-bubble">
                          <AnswerText segments={m.content} onCopy={noteCopy} />
                        </div>
                      ) : loading && i === messages.length - 1 ? (
                        <div className="dots" role="status" aria-label="PocketAI is working">
                          <span className="dot" />
                          <span className="dot" />
                          <span className="dot" />
                        </div>
                      ) : null}
                    </div>
                  )
                )}
              {messages !== null && copyNote && (
                <div className="copy-note" aria-live="polite">
                  {copyNote}
                </div>
              )}
            </div>

            <div className="composer-wrap">
              <div className="composer">
                <textarea
                  ref={inputRef}
                  rows={1}
                  aria-label="Message"
                  placeholder="Ask about a file, a folder, or the web"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      submit();
                    }
                  }}
                />
                {micSupported && (
                  <button
                    type="button"
                    className={`icon-btn${listening ? " listening" : ""}`}
                    aria-label="Speak your message"
                    onClick={toggleMic}
                  >
                    <MicIcon />
                  </button>
                )}
                {loading ? (
                  <button type="button" className="send-btn stop" aria-label="Stop" onClick={stop}>
                    <span className="stop-square" />
                  </button>
                ) : (
                  <button type="button" className="send-btn" aria-label="Send" onClick={() => submit()}>
                    <SendIcon />
                  </button>
                )}
              </div>
              <p className="composer-hint phone-hide">Enter sends. Shift and Enter adds a line.</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
