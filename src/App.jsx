import { useEffect, useState } from "react";
import Home from "./pages/Home";
import Chat from "./pages/Chat";
import { fetchServerInfo } from "./lib/chatApi";
import "./App.css";

// Two views, like the mockups: the home page and the browser chat.
// The chat lives at #chat so the home page's section anchors
// (#demo, #tools, #install) keep working as plain links.
export default function App() {
  const [view, setView] = useState(() => (window.location.hash === "#chat" ? "chat" : "home"));
  const [storedModel, setStoredModel] = useState(() => {
    try {
      return localStorage.getItem("pocketai-model");
    } catch {
      return null;
    }
  });
  const [serverInfo, setServerInfo] = useState(null);
  const [serverDown, setServerDown] = useState(false);

  useEffect(() => {
    const onHash = () => setView(window.location.hash === "#chat" ? "chat" : "home");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (view === "chat") window.scrollTo(0, 0);
  }, [view]);

  useEffect(() => {
    fetchServerInfo()
      .then((info) => {
        setServerInfo(info);
        setServerDown(false);
      })
      .catch(() => setServerDown(true));
  }, []);

  // The model the chat should use: the visitor's saved pick when this
  // server can actually serve it, otherwise the server's own default
  // (Claude on the hosted site, Llama on a local install). A pick the
  // server can't serve is never honoured silently — the chat page
  // shows which backend is active and only offers working ones.
  const backendAvailable = (id) =>
    !serverInfo || serverInfo.backends?.[id]?.available !== false;
  const modelId =
    storedModel && backendAvailable(storedModel)
      ? storedModel
      : serverInfo?.default_backend || storedModel || "llama";

  // The home page's install tabs follow the visitor's own pick, never the
  // availability adjustment above: installing Llama on your own computer
  // has nothing to do with what this server can serve. Feeding the tabs
  // modelId instead made the Llama tab unselectable on the hosted site —
  // every click snapped straight back to Claude.
  const installModelId = storedModel || "llama";

  const pickModel = (id) => {
    setStoredModel(id);
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
    <Chat
      onBack={backHome}
      modelId={modelId}
      onPickModel={pickModel}
      serverInfo={serverInfo}
      serverDown={serverDown}
    />
  ) : (
    <Home onOpenChat={openChat} modelId={installModelId} onPickModel={pickModel} />
  );
}
