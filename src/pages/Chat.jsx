import { useCallback, useEffect, useRef, useState } from "react";
import { RUNS, INSTALLS, matchRun } from "../data/samples";
import { fetchAgentName, streamChat, toolArg } from "../lib/chatApi";
import { Logo, MicIcon, SendIcon, ToolStep, AnswerText } from "../components/ui";

const STATE_BUTTONS = [
  ["empty", "Empty"],
  ["working", "Working"],
  ["run", "Answer"],
  ["offline", "Server not running"],
];

export default function Chat({ onBack, modelId }) {
  const model = INSTALLS.find((i) => i.id === modelId) || INSTALLS[0];
  const [agentName, setAgentName] = useState("PocketAI");
  const [conn, setConn] = useState("checking"); // checking | live | offline

  // Demo (mockup) state — used until a live conversation starts, and
  // whenever the local server is not running. Works with no API key.
  const [demoState, setDemoState] = useState("empty"); // empty|working|run|unknown|offline
  const [demoRun, setDemoRun] = useState(0);
  const [asked, setAsked] = useState("");
  const [draft, setDraft] = useState("");
  const [copyNote, setCopyNote] = useState("");
  const [copiedPath, setCopiedPath] = useState("");

  // Live conversation state (previous frontend's behaviour, restyled).
  const [messages, setMessages] = useState(null); // null = demo/preview
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [editingIdx, setEditingIdx] = useState(null);
  const [editDraft, setEditDraft] = useState("");
  const abortRef = useRef(null);
  const recogRef = useRef(null);
  const inputRef = useRef(null);
  const scrollRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    fetchAgentName()
      .then((name) => {
        if (name) setAgentName(name);
        setConn("live");
      })
      .catch(() => {
        setConn("offline");
        setDemoState("offline");
      });
    return () => clearTimeout(timerRef.current);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, demoState]);

  const noteCopy = useCallback((path) => {
    setCopiedPath(path);
    setCopyNote(`Copied ${path}`);
  }, []);

  // ── Demo runs ──────────────────────────────────────────────────────────
  const goDemo = useCallback((j, text) => {
    clearTimeout(timerRef.current);
    setDemoRun(j);
    setAsked(text);
    setDemoState("working");
    setCopyNote("");
    setCopiedPath("");
    timerRef.current = setTimeout(() => setDemoState("run"), 1300);
  }, []);

  const pickState = (mode) => {
    setMessages(null);
    if (mode === "working") goDemo(demoRun, RUNS[demoRun].ask);
    else {
      clearTimeout(timerRef.current);
      setAsked(RUNS[demoRun].ask);
      setDemoState(mode);
    }
  };

  // ── Live sending (SSE, same contract as before) ───────────────────────
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
        if (e.name !== "AbortError") {
          // Server went away mid-chat: fall back to the mockup's
          // "not running" state instead of a dead thread.
          setConn("offline");
          setMessages(null);
          setDemoState("offline");
        }
      }
      setLoading(false);
      inputRef.current?.focus();
    },
    [modelId]
  );

  const send = () => {
    const text = draft.trim();
    if (!text || loading) return;
    setDraft("");
    if (messages !== null || conn === "live") {
      sendLive(text, messages || []);
    } else {
      const j = matchRun(text);
      if (j < 0) {
        setAsked(text);
        setDemoState("unknown");
      } else goDemo(j, text);
    }
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
  const demoFiles = demoState === "run" ? RUNS[demoRun].files : [];
  const liveFiles = [];
  if (messages) {
    for (const m of messages) {
      for (const tc of m.toolCalls || []) {
        if (tc.arg && (tc.name === "read_file" || tc.name === "read_pdf" || tc.name === "list_directory")) {
          if (!liveFiles.some((f) => f.name === tc.arg)) {
            liveFiles.push({
              name: tc.arg,
              hint: tc.name === "list_directory" ? "Folder" : tc.name === "read_pdf" ? "PDF" : "File",
            });
          }
        }
      }
    }
  }
  const files = messages !== null ? liveFiles : demoFiles;

  const copyFile = (name) => {
    try {
      navigator.clipboard.writeText(name);
    } catch {
      /* ignore */
    }
    noteCopy(name);
  };

  const r = RUNS[demoRun];
  const showThread = messages !== null || demoState === "working" || demoState === "run" || demoState === "unknown";

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
        {messages === null && (
          <>
            <span className="phone-hide">Mockup states:</span>
            <div role="group" aria-label="Mockup state" className="state-group phone-hide">
              {STATE_BUTTONS.map(([mode, label]) => (
                <button
                  key={mode}
                  type="button"
                  className="state-btn"
                  aria-pressed={demoState === mode}
                  style={{
                    borderColor: demoState === mode ? "#1c2630" : "#b6bdc6",
                    background: demoState === mode ? "#ecd9a0" : "#fdfdfc",
                  }}
                  onClick={() => pickState(mode)}
                >
                  {label}
                </button>
              ))}
            </div>
            <span className="phone-hide">Type one of the sample questions, or tap a chip.</span>
          </>
        )}
        {messages !== null && <span>Connected to {agentName} on this computer.</span>}
        <span className="phone-only mono model-badge">{model.modelLabel}, local</span>
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
                  Nothing yet. Each file PocketAI opens in this chat is filed here, and you can copy its path.
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
          <div className="model-note">
            Model <span className="mono">{model.modelLabel}</span>
            {model.id === "llama" ? ", running on this computer. Nothing is sent anywhere." : ", via Anthropic."}
          </div>
        </aside>

        <section className="chat-main">
          <div className="chat-card">
            <div className="thread" aria-live="polite" ref={scrollRef}>
              {/* ── Demo / preview thread ─────────────────────────────── */}
              {messages === null && demoState === "empty" && (
                <div className="empty-state">
                  <h1>What should I look up?</h1>
                  <p>Ask about a file, a folder, or anything on the web. I will say which tool I am using.</p>
                  <div className="chips">
                    {RUNS.map((x, j) => (
                      <button key={x.key} type="button" className="chip" onClick={() => goDemo(j, x.ask)}>
                        {x.ask}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages === null && showThread && (
                <div className="user-row">
                  <div className="bubble user">{asked || r.ask}</div>
                  <button
                    type="button"
                    className="edit-link"
                    onClick={() => {
                      setDraft(asked || r.ask);
                      setDemoState("empty");
                      inputRef.current?.focus();
                    }}
                  >
                    Edit and resend
                  </button>
                </div>
              )}

              {messages === null && demoState === "working" && (
                <div className="answer-block">
                  <ToolStep tool={r.tool} arg={r.arg} note="looking" dashed />
                  <div className="dots" role="status" aria-label="PocketAI is working">
                    <span className="dot" />
                    <span className="dot" />
                    <span className="dot" />
                  </div>
                </div>
              )}

              {messages === null && demoState === "run" && (
                <div className="answer-block">
                  <div className="steps">
                    {r.steps.map((s, i) => (
                      <ToolStep key={i} tool={s.tool} arg={s.arg} note={s.note} stamp={s.stamp} />
                    ))}
                  </div>
                  <div className="bubble assistant answer-bubble">
                    <AnswerText segments={r.answer} onCopy={noteCopy} />
                  </div>
                  {r.followup && (
                    <div className="phone-only followup">
                      <div className="user-row">
                        <div className="bubble user">{r.followup.ask}</div>
                      </div>
                      <div className="bubble assistant answer-bubble">
                        <AnswerText segments={r.followup.answer} onCopy={noteCopy} />
                      </div>
                    </div>
                  )}
                  <div className="copy-note" aria-live="polite">
                    {copyNote}
                  </div>
                </div>
              )}

              {messages === null && demoState === "unknown" && (
                <div className="unknown-note">
                  This mockup only knows the three sample questions. In the real app, anything you type is sent to the
                  model.
                </div>
              )}

              {messages === null && demoState === "offline" && (
                <div className="offline-card">
                  <h1>PocketAI is not running on this computer</h1>
                  <p>
                    This page talks to a small server on your own machine, and it did not answer. Start it, then send
                    your message again.
                  </p>
                  <code className="mono offline-cmd">python server/app.py</code>
                  <p className="offline-more">Have not installed it yet? The home page has the one command install.</p>
                </div>
              )}

              {/* ── Live thread ───────────────────────────────────────── */}
              {messages !== null &&
                messages.map((m, i) =>
                  m.role === "user" ? (
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
                      send();
                    }
                  }}
                />
                <button
                  type="button"
                  className={`icon-btn${listening ? " listening" : ""}`}
                  aria-label="Speak your message"
                  onClick={toggleMic}
                >
                  <MicIcon />
                </button>
                {loading ? (
                  <button type="button" className="send-btn stop" aria-label="Stop" onClick={stop}>
                    <span className="stop-square" />
                  </button>
                ) : (
                  <button type="button" className="send-btn" aria-label="Send" onClick={send}>
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
