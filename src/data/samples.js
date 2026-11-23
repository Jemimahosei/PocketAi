// Sample content, copied from Jemimah's PocketAI mockups.
// Used for the home-page sample runs and for the browser-chat demo mode
// (which works with no server and no API key).

export const RUNS = [
  {
    name: "Read a PDF",
    ask: "When is my lease up for renewal?",
    key: "lease",
    tool: "read_pdf",
    arg: "~/Documents/lease.pdf",
    steps: [
      { tool: "list_directory", arg: "~/Documents", note: "14 items", stamp: false },
      { tool: "read_pdf", arg: "~/Documents/lease.pdf", note: "3 pages read", stamp: true },
    ],
    answer: [
      { t: "Your lease ends on ", w: 400 },
      { t: "August 31", w: 700 },
      { t: ". Section 4 of ", w: 400 },
      { t: "~/Documents/lease.pdf", path: true },
      { t: " asks for written notice at least 60 days before the end date, so your notice is due by ", w: 400 },
      { t: "July 2", w: 700 },
      { t: ".", w: 400 },
    ],
    // Shorter plain version used by the home-page sample panel.
    homeAnswer: [
      { t: "Your lease ends on ", w: 400 },
      { t: "August 31", w: 700 },
      { t: ". Section 4 asks for written notice at least 60 days before the end date, so your notice is due by ", w: 400 },
      { t: "July 2", w: 700 },
      { t: ". The same section says rent cannot rise more than 3 percent at renewal.", w: 400 },
    ],
    files: [{ name: "~/Documents/lease.pdf", hint: "PDF, 3 pages" }],
    // Extra exchange shown in the phone chat mockup.
    followup: {
      ask: "Can rent go up at renewal?",
      answer: [
        { t: "Yes, but by no more than ", w: 400 },
        { t: "3 percent", w: 700 },
        { t: ", according to the same section.", w: 400 },
      ],
    },
  },
  {
    name: "Look in a folder",
    ask: "What is on my Desktop?",
    key: "desktop",
    tool: "list_directory",
    arg: "~/Desktop",
    steps: [{ tool: "list_directory", arg: "~/Desktop", note: "7 items", stamp: false }],
    answer: [
      { t: "Two folders, ", w: 400 },
      { t: "Receipts", w: 700 },
      { t: " and ", w: 400 },
      { t: "Thesis", w: 700 },
      { t: ", and five files: resume.pdf, three screenshots and ", w: 400 },
      { t: "~/Desktop/notes.txt", path: true },
      { t: ". Want me to read the notes?", w: 400 },
    ],
    homeAnswer: [
      { t: "Two folders, ", w: 400 },
      { t: "Receipts", w: 700 },
      { t: " and ", w: 400 },
      { t: "Thesis", w: 700 },
      { t: ", and five files: resume.pdf, notes.txt and three screenshots. Want me to read notes.txt?", w: 400 },
    ],
    files: [{ name: "~/Desktop", hint: "Folder, 7 items" }],
  },
  {
    name: "Search the web",
    ask: "What does the Web Speech API do?",
    key: "speech",
    tool: "search_web",
    arg: "Web Speech API",
    steps: [{ tool: "search_web", arg: "Web Speech API", note: "1 summary, 5 related", stamp: false }],
    answer: [
      {
        t: "It lets a web page turn speech into text and text into speech, using the browser. The microphone button in this chat uses the speech to text half.",
        w: 400,
      },
    ],
    homeAnswer: [
      { t: "It lets a web page turn speech into text and text into speech, using the browser. ", w: 400 },
      { t: "PocketAI's browser chat uses the speech to text half", w: 700 },
      { t: " for the microphone button.", w: 400 },
    ],
    files: [],
  },
];

export function matchRun(text) {
  const t = (text || "").toLowerCase();
  return RUNS.findIndex(
    (r) => t.includes(r.key) || t.includes(r.ask.toLowerCase()) || (r.key === "speech" && t.includes("web speech"))
  );
}

// The two install paths from the mockups. "llama" is the free local-model
// path, built into the UI for real: picking it sets the model the chat
// sidebar reports, and its demo runs never leave the machine.
export const INSTALLS = [
  {
    id: "llama",
    name: "Free, with Llama",
    cmd: "curl -fsSL https://raw.githubusercontent.com/Jemimahosei/PocketAi/main/install.sh -o /tmp/pocketai-install.sh && bash /tmp/pocketai-install.sh",
    blurb:
      "Installs Ollama if you do not have it, downloads the Llama 3.2 model, then starts PocketAI. No account and no API key.",
    privacy: "Nothing leaves your computer. The model runs on your machine.",
    modelLabel: "Llama 3.2",
    modelNote: "Model Llama 3.2, running on this computer. Nothing is sent anywhere.",
  },
  {
    id: "claude",
    name: "Smarter, with Claude",
    cmd: "curl -fsSL https://raw.githubusercontent.com/Jemimahosei/PocketAi/main/install-claude.sh -o /tmp/pocketai-install-claude.sh && bash /tmp/pocketai-install-claude.sh",
    blurb:
      "Asks for an Anthropic API key once, saves it on your computer, then starts PocketAI. Answers are sharper on long documents.",
    privacy: "The text of files you ask about is sent to Anthropic to answer your question. Nothing else is.",
    modelLabel: "Claude",
    modelNote: "Model Claude, via Anthropic. The text of files you ask about is sent to Anthropic.",
  },
];

export const TOOLS = [
  { name: "read_file", text: "Opens a text file, such as notes, code, CSVs or Markdown.", phoneText: "Opens a text file, such as notes, code, CSVs or Markdown." },
  { name: "read_pdf", text: "Reads the text inside a PDF, up to the first 30,000 characters.", phoneText: "Reads the text inside a PDF." },
  { name: "list_directory", text: "Looks inside a folder to find the file you mean.", phoneText: "Looks inside a folder to find the file you mean." },
  { name: "search_web", text: "Searches DuckDuckGo when the answer is not in your files.", phoneText: "Searches DuckDuckGo when the answer is not in your files." },
];

export const GITHUB_URL = "https://github.com/Jemimahosei/PocketAi";
// Local dev: the Vite server (5173) talks to Flask on 5001.
// Production build: the Flask server serves this app itself, so the
// API is same-origin and the base URL is empty.
export const SERVER_URL = import.meta.env.DEV ? "http://localhost:5001" : "";
