import { useState } from "react";

export function Logo({ size = 30 }) {
  return (
    <svg width={size} height={Math.round(size * 0.8)} viewBox="0 0 30 24" aria-hidden="true">
      <path
        d="M1 5a3 3 0 0 1 3-3h7l3 3h12a3 3 0 0 1 3 3v13a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1z"
        fill="#ecd9a0"
        stroke="#1c2630"
        strokeWidth="2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function MicIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </svg>
  );
}

export function SendIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  );
}

// One tool step row, as drawn in the mockups (mono, cream, tool / arg / note).
export function ToolStep({ tool, arg, note, stamp, dashed, expandable, expanded, onToggle, result }) {
  return (
    <div className={`tool-step${dashed ? " dashed" : ""}`}>
      <div className="tool-step-main" onClick={expandable ? onToggle : undefined} role={expandable ? "button" : undefined}>
        <strong>{tool}</strong>
        <span className="tool-arg">{arg}</span>
        {note && <span className="tool-note">{note}</span>}
        {stamp && <span className="stamp">PULLED</span>}
      </div>
      {expandable && expanded && result && <div className="tool-result">{result}</div>}
    </div>
  );
}

// Clickable file path inside an answer; copies the path.
export function PathChip({ path, onCopy }) {
  const copy = () => {
    try {
      navigator.clipboard.writeText(path);
    } catch {
      /* clipboard unavailable */
    }
    onCopy?.(path);
  };
  return (
    <button type="button" className="path-chip mono" onClick={copy} aria-label="Copy path">
      {path}
    </button>
  );
}

// Renders answer segments ({t, w} text runs and {t, path:true} path chips),
// preserving the previous frontend's habit of linkifying file paths in
// plain live answers.
const PATH_RE = /(~\/[^\s,'")\]]+|\/Users\/[^\s,'")\]]+|\/[a-zA-Z][^\s,'")\]]*\.(pdf|txt|md|py|js|json|csv|docx|xlsx|png|jpg))/g;

export function AnswerText({ segments, onCopy }) {
  if (typeof segments === "string") {
    const parts = [];
    let last = 0;
    let m;
    const re = new RegExp(PATH_RE.source, "g");
    while ((m = re.exec(segments)) !== null) {
      if (m.index > last) parts.push({ t: segments.slice(last, m.index), w: 400 });
      parts.push({ t: m[0], path: true });
      last = m.index + m[0].length;
    }
    if (last < segments.length) parts.push({ t: segments.slice(last), w: 400 });
    segments = parts;
  }
  return (
    <>
      {segments.map((p, i) =>
        p.path ? (
          <PathChip key={i} path={p.t} onCopy={onCopy} />
        ) : (
          <span key={i} style={{ fontWeight: p.w || 400 }}>
            {p.t}
          </span>
        )
      )}
    </>
  );
}

export function CopyButton({ text, className = "", full = false }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    try {
      navigator.clipboard
        .writeText(text)
        .then(() => setCopied(true), () => setCopied(true))
        .catch(() => {});
    } catch {
      /* ignore */
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };
  return (
    <button type="button" className={`copy-btn ${className}`} style={full ? { width: "100%" } : undefined} onClick={copy} aria-live="polite">
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export function FolderTabs({ tabs, current, onPick, ariaLabel }) {
  return (
    <div role="group" aria-label={ariaLabel} className="folder-tabs">
      {tabs.map((t, j) => (
        <button
          key={t.name}
          type="button"
          className="ftab"
          aria-pressed={j === current}
          onClick={() => onPick(j)}
          style={{
            background: j === current ? "#ecd9a0" : "#fdfdfc",
            marginBottom: j === current ? "-2px" : "0",
          }}
        >
          {t.name}
        </button>
      ))}
    </div>
  );
}
