import { useEffect, useState } from "react";
import Home from "./pages/Home";
import Chat from "./pages/Chat";
import "./App.css";

// Two views, like the mockups: the home page and the browser chat.
// The chat lives at #chat so the home page's section anchors
// (#demo, #tools, #install) keep working as plain links.
export default function App() {
  const [view, setView] = useState(() => (window.location.hash === "#chat" ? "chat" : "home"));
  const [modelId, setModelId] = useState(() => {
    try {
      return localStorage.getItem("pocketai-model") || "llama";
    } catch {
      return "llama";
    }
  });

  useEffect(() => {
    const onHash = () => setView(window.location.hash === "#chat" ? "chat" : "home");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (view === "chat") window.scrollTo(0, 0);
  }, [view]);

  const pickModel = (id) => {
    setModelId(id);
    try {
      localStorage.setItem("pocketai-model", id);
    } catch {
      /* private mode */
    }
  };

  const openChat = () => {
    window.location.hash = "#chat";
    setView("chat");
  };
  const backHome = () => {
    window.location.hash = "";
    setView("home");
  };

  return view === "chat" ? (
    <Chat onBack={backHome} modelId={modelId} />
  ) : (
    <Home onOpenChat={openChat} modelId={modelId} onPickModel={pickModel} />
  );
}
