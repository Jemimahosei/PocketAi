import { useState } from "react";
import { RUNS, INSTALLS, TOOLS, GITHUB_URL } from "../data/samples";
import { Logo, ToolStep, AnswerText, CopyButton, FolderTabs } from "../components/ui";

export default function Home({ onOpenChat, modelId, onPickModel }) {
  const [run, setRun] = useState(0);
  const inst = INSTALLS.findIndex((i) => i.id === modelId);
  const instIdx = inst >= 0 ? inst : 0;
  const r = RUNS[run];

  return (
    <div className="page home">
      <header className="site-header">
        <div className="wrap header-in">
          <a className="brand" href="#" onClick={(e) => e.preventDefault()}>
            <Logo />
            PocketAI
          </a>
          <nav aria-label="Main" className="main-nav">
            <a className="nav-link" href="#demo">Sample runs</a>
            <a className="nav-link" href="#tools">What it can do</a>
            <a className="nav-link" href="#install">Install</a>
            <button type="button" className="nav-link as-btn" onClick={onOpenChat}>Browser chat</button>
            <a className="btn-dark nav-cta" href={GITHUB_URL}>Source on GitHub</a>
          </nav>
          <a className="btn-dark header-gh" href={GITHUB_URL}>GitHub</a>
        </div>
      </header>

      <main className="wrap">
        <section className="hero">
          <div className="hero-copy">
            <h1>Ask questions about your own files.</h1>
            <p className="lede">
              PocketAI opens the documents, PDFs and folders on your computer, searches the web when it needs to, and
              answers with what it found. It runs in your terminal or in a browser tab.
            </p>
            <div className="hero-ctas">
              <a className="btn-dark btn-lg" href="#install">Install it</a>
              <a className="btn-outline btn-lg phone-hide" href="#demo">See a sample run</a>
              <button type="button" className="btn-outline btn-lg phone-only" onClick={onOpenChat}>
                Open the browser chat
              </button>
            </div>
          </div>
          <div className="hero-card-wrap phone-hide">
            <div aria-hidden="true" className="hero-card-shadow" />
            <div className="hero-card">
              <div className="mono hero-path">~/Documents</div>
              <div className="mono hero-files">
                <div>lease.pdf</div>
                <div>resume.pdf</div>
                <div>notes.txt</div>
                <div>Receipts/</div>
                <div>Thesis/</div>
              </div>
              <div className="hero-q">&quot;When is my lease up for renewal?&quot;</div>
              <div className="mono hero-stamp">PULLED lease.pdf</div>
            </div>
          </div>
        </section>

        <section id="demo" className="section demo">
          <h2>
            <span className="phone-hide">Three sample runs</span>
            <span className="phone-only">A sample run</span>
          </h2>
          <p className="section-sub phone-hide">
            These are written examples of how a conversation goes, with made up files. This page cannot open anything
            on your computer. PocketAI running on your machine can.
          </p>
          <p className="section-sub phone-only">
            A written example with made up files. This page cannot open anything on your device.
          </p>

          <div className="phone-hide">
            <FolderTabs tabs={RUNS} current={run} onPick={setRun} ariaLabel="Choose a sample run" />
          </div>
          <div className="folder-panel">
            <div className="folder-card">
              <div className="bubble user demo-ask">{r.ask}</div>
              <div className="steps">
                {r.steps.map((s, i) => (
                  <ToolStep key={i} tool={s.tool} arg={s.arg} note={s.note} />
                ))}
              </div>
              <div className="demo-answer">
                <AnswerText segments={r.homeAnswer} />
              </div>
            </div>
          </div>
          <p className="fineprint phone-hide">
            Sample conversations written for this page. Real runs show the same steps, because PocketAI lists every
            tool it uses.
          </p>
        </section>

        <section id="tools" className="section">
          <h2>Four things it can do</h2>
          <p className="section-sub phone-hide">The assistant decides which to use. You see each one as it happens.</p>
          <div className="tools-grid">
            {TOOLS.map((t) => (
              <div key={t.name} className="tool-card">
                <div className="mono tool-name">{t.name}</div>
                <p>
                  <span className="phone-hide">{t.text}</span>
                  <span className="phone-only">{t.phoneText}</span>
                </p>
              </div>
            ))}
          </div>
          <p className="tools-note phone-hide">
            Also in the browser chat: answers stream in as they are written, you can speak a question, edit an earlier
            message and resend it, and copy any file path in a reply with one click.
          </p>
        </section>

        <section id="install" className="section">
          <h2>Install it in one command</h2>
          <p className="section-sub">
            <span className="phone-hide">Needs a Mac or Linux terminal. Pick the model that does the thinking.</span>
            <span className="phone-only">Run it in a Mac or Linux terminal. Pick the model that does the thinking.</span>
          </p>
          <FolderTabs
            tabs={INSTALLS}
            current={instIdx}
            onPick={(j) => onPickModel(INSTALLS[j].id)}
            ariaLabel="Choose a model"
          />
          <div className="folder-panel install-panel">
            <p className="install-blurb">{INSTALLS[instIdx].blurb}</p>
            <div className="install-row">
              <code className="mono install-cmd">{INSTALLS[instIdx].cmd}</code>
              <span className="phone-hide">
                <CopyButton text={INSTALLS[instIdx].cmd} />
              </span>
            </div>
            <div className="phone-only install-copy-full">
              <CopyButton text={INSTALLS[instIdx].cmd} full />
            </div>
            <p className="install-privacy">{INSTALLS[instIdx].privacy}</p>
          </div>
          <p className="install-more phone-hide">
            Prefer to read it first? The{" "}
            <a href={GITHUB_URL} className="text-link">source is on GitHub</a>, and the README covers running the
            browser chat from a checkout.
          </p>
        </section>

        <section className="section privacy-section phone-hide">
          <div className="privacy-card">
            <div className="privacy-copy">
              <h2 className="privacy-title">Your files stay on your computer.</h2>
              <p>
                The tools run locally. Only the text you ask about goes to the model, and with the free Llama option
                that model runs on your machine too.
              </p>
            </div>
            <button type="button" className="btn-dark btn-lg" onClick={onOpenChat}>
              Open the browser chat
            </button>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="wrap footer-in">
          <span>Built by Jemimah Osei, Cornell Information Science.</span>
          <span className="phone-hide">PocketAI is open source on GitHub.</span>
          <span className="phone-only">PocketAI is open source on GitHub.</span>
        </div>
      </footer>
    </div>
  );
}
