// src/Chat.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bot,
  Plus,
  Cog,
  Search as SearchIcon,
  Play,
  CalendarDays,
  MapPin,
  History as HistoryIcon,
  Trash2,
} from "lucide-react";

// Prefer env var; fall back to Vite proxy "/api"
const API_BASE = import.meta.env.VITE_API_BASE?.replace(/\/+$/, "") || "/api";

// -------------------- helpers: storage --------------------
const SESSIONS_KEY = "unibot.sessions.v1";
const FEEDBACK_KEY = "unibot.feedback.v1";

const makeSession = () => {
  const id = String(Date.now());
  return {
    id,
    title: "New chat",
    createdAt: new Date().toISOString(),
    messages: [{ role: "assistant", text: "Hi, I’m UniBot — ask me anything about UIU." }],
  };
};

const loadSessions = () => {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    if (!raw) return [makeSession()];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length === 0) return [makeSession()];
    return parsed;
  } catch {
    return [makeSession()];
  }
};

const saveSessions = (sessions) => {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
  } catch {}
};

const saveFeedbackLocal = (item) => {
  try {
    const arr = JSON.parse(localStorage.getItem(FEEDBACK_KEY) || "[]");
    arr.push(item);
    localStorage.setItem(FEEDBACK_KEY, JSON.stringify(arr));
  } catch {}
};

const NavLink = ({ children, href = "#" }) => (
  <a
    href={href}
    className="px-5 py-2 text-base font-semibold text-zinc-100/90 hover:text-white transition"
  >
    {children}
  </a>
);

function renderRich(text) {
  const parts = [];
  const regex = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
  let lastIndex = 0,
    match;
  while ((match = regex.exec(text)) !== null) {
    const before = text.slice(lastIndex, match.index);
    if (before) parts.push(before);
    parts.push(
      <a
        key={`${match.index}-${match[2]}`}
        className="underline decoration-zinc-400 hover:text-white"
        href={match[2]}
        target="_blank"
        rel="noreferrer"
      >
        {match[1]}
      </a>
    );
    lastIndex = regex.lastIndex;
  }
  const tail = text.slice(lastIndex);
  if (tail) parts.push(tail);
  return parts;
}

// Small pretty date
const fmt = (iso) => {
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso || "";
  }
};

export default function Chat() {
  // -------------------- sessions state --------------------
  const [sessions, setSessions] = useState(loadSessions);
  const [activeId, setActiveId] = useState(() => sessions[0]?.id);
  const active = useMemo(() => sessions.find((s) => s.id === activeId) || sessions[0], [sessions, activeId]);

  // derived: messages bound to active session
  const [messages, setMessages] = useState(active?.messages || []);
  useEffect(() => {
    setMessages(active?.messages || []);
  }, [activeId]); // switch session -> load its messages

  // persist on changes
  useEffect(() => {
    // write back messages to active session
    setSessions((prev) => {
      const next = prev.map((s) => (s.id === activeId ? { ...s, messages } : s));
      saveSessions(next);
      return next;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorText, setErrorText] = useState("");
  const [showHistory, setShowHistory] = useState(false);

  const scrollerRef = useRef(null);

  const questions = useMemo(
    () => [
      "What is the full name and address of the university?",
      "Who is the Vice-Chancellor right now?",
      "When was the university established?",
      "When does the Fall 2025 of CSE Department start ?",
      "What is the last date to register for courses of Summer 2025?",
      "When are the Admission tests scheduled of Fall 2025?",
    ],
    []
  );

  // autoscroll
  useEffect(() => {
    const el = scrollerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  // smooth scroll to #hash (navbar Feedback)
  useEffect(() => {
    const scrollToHash = () => {
      const { hash } = window.location;
      if (hash) {
        const el = document.querySelector(hash);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    };
    scrollToHash();
    window.addEventListener("hashchange", scrollToHash);
    return () => window.removeEventListener("hashchange", scrollToHash);
  }, []);

  // derive session title from first user message
  const maybeRetitle = (msgs) => {
    const firstUser = msgs.find((m) => m.role === "user");
    const title =
      firstUser?.text?.slice(0, 60) ||
      msgs.find((m) => m.role === "assistant")?.text?.slice(0, 60) ||
      "New chat";
    setSessions((prev) => {
      const next = prev.map((s) => (s.id === activeId ? { ...s, title } : s));
      saveSessions(next);
      return next;
    });
  };

  // -------------------- actions --------------------
  const newChat = () => {
    const fresh = makeSession();
    setSessions((prev) => {
      const next = [fresh, ...prev]; // newest first
      saveSessions(next);
      return next;
    });
    setActiveId(fresh.id);
    setMessages(fresh.messages);
    setInput("");
    setErrorText("");
  };

  const restoreSession = (sid) => {
    setActiveId(sid);
    const picked = sessions.find((s) => s.id === sid);
    setMessages(picked?.messages || []);
    setShowHistory(false);
  };

  const deleteSession = (sid) => {
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== sid);
      // ensure at least one session exists
      const ensured = next.length ? next : [makeSession()];
      saveSessions(ensured);
      // if deleting active, switch
      if (sid === activeId) {
        setActiveId(ensured[0].id);
        setMessages(ensured[0].messages);
      }
      return ensured;
    });
  };

  async function send(questionOverride) {
    if (loading) return;
    const q = (questionOverride ?? input).trim();
    if (!q) return;

    setErrorText("");
    const newMsgs = [...messages, { role: "user", text: q }];
    setMessages(newMsgs);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`API ${res.status}: ${txt || res.statusText}`);
      }
      const data = await res.json();
      // Backend returns: { answer: string, citations: [{url, id, score}, ...] }
      const src = (data?.citations || [])
        .map((s, i) => (s?.url ? `[${i + 1}](${s.url})` : null))
        .filter(Boolean)
        .join(" ");
      const text = data?.answer || "Sorry—no answer returned.";

      const updated = [
        ...newMsgs,
        {
          role: "assistant",
          text: `${text}${src ? `\n\nSources: ${src}` : ""}`,
        },
      ];
      setMessages(updated);

      // set a title if it's still the default
      const sess = sessions.find((s) => s.id === activeId);
      if (sess && (!sess.title || sess.title === "New chat")) {
        maybeRetitle(updated);
      }
    } catch (err) {
      setErrorText(
        err?.message?.includes("Failed to fetch")
          ? "Cannot reach the server. Is the backend running?"
          : err?.message || "Something went wrong."
      );
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: "Sorry—something went wrong. Please try again or check the backend.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const quickAsk = (q) => send(q);

  // -------------------- feedback submit --------------------
  const onSubmitFeedback = async (e) => {
    e.preventDefault();
    const name = e.target.name.value.trim();
    const message = e.target.message.value.trim();
    if (!message) return alert("Please enter your feedback first!");
    const payload = { name, message, createdAt: new Date().toISOString() };

    try {
      const res = await fetch(`${API_BASE}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Server rejected feedback");
      alert("Thank you for your feedback! ❤️");
      e.target.reset();
    } catch {
      // Fallback to local storage if backend route is not implemented
      saveFeedbackLocal(payload);
      alert("Thank you! Saved locally (offline).");
      e.target.reset();
    }
  };

  // -------------------- UI --------------------
  return (
    <div className="min-h-screen bg-[#1b1f2a] text-white flex flex-col">
      <div className="h-1 w-full bg-teal-700/70 shrink-0" />
      <header className="bg-[#2a2f3a] shrink-0">
        <div className="w-full max-w-[1600px] mx-auto px-6 lg:px-24">
          <div className="h-16 flex items-center justify-between">
            <a href="/" className="flex items-center gap-2 font-bold text-xl">
              <div className="grid place-items-center bg-white/10 rounded-lg p-1">
                <Bot className="w-5 h-5" />
              </div>
              <span>UniBot</span>
            </a>
            <nav className="absolute left-1/2 -translate-x-1/2 hidden md:flex">
              <ul className="flex items-center">
                <li>
                  <NavLink href="/">Home</NavLink>
                </li>
                <li>
                  <NavLink href="/#about">About</NavLink>
                </li>
                <li>
                  <NavLink href="/chat">Ask UniBot</NavLink>
                </li>
                <li>
                  <NavLink href="/feedback">Feedback</NavLink>
                </li>
              </ul>
            </nav>
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-2 rounded-full bg-white/10 border border-white/10 px-4 py-2">
                <SearchIcon className="w-4 h-4" />
                <input
                  placeholder="search here"
                  className="bg-transparent outline-none text-sm placeholder:text-zinc-300 w-40"
                />
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 min-h-0 w-full max-w-[1600px] mx-auto px-6 lg:px-24 py-6 grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6">
        {/* Sidebar */}
        <aside className="h-full min-w-0 rounded-lg bg-[linear-gradient(180deg,#2b313d,#262c37)] border border-cyan-700/40 relative overflow-y-auto">
          <div className="p-4 border-b border-cyan-700/40 flex items-center gap-2 font-semibold">
            <button
              onClick={newChat}
              className="flex items-center gap-2 hover:text-white transition"
            >
              <Plus className="w-4 h-4" /> New Chat
            </button>

            <button
              onClick={() => setShowHistory(true)}
              className="ml-auto flex items-center gap-2 text-sm bg-white/10 hover:bg-white/15 px-3 py-1.5 rounded-full transition"
              title="Open history"
            >
              <HistoryIcon className="w-4 h-4" /> History
            </button>
          </div>

          <div className="p-4 space-y-3 text-zinc-200">
            {questions.map((q, i) => (
              <button
                key={i}
                onClick={() => quickAsk(q)}
                className="w-full text-left text-[15px] leading-snug hover:text-white transition"
              >
                {q}
              </button>
            ))}
          </div>

          <div className="px-4 pb-16">
            <div className="mt-5 grid gap-4 sm:flex-cols-2">
              <Link
                to="/calendar"
                className="text-left whitespace-pre-line rounded-2xl bg-white/5 border-2 border-cyan-700/50 px-5 py-5 hover:bg-white/10 transition shadow-[0_1px_0_0_rgba(255,255,255,0.05)_inset]"
              >
                <div className="mb-3 grid place-items-center">
                  <CalendarDays className="w-7 h-7" />
                </div>
                <div className="text-center font-extrabold text-[16px] leading-5">
                  Academic{"\n"}Calendar
                </div>
              </Link>
              <Link
                to="/map"
                className="text-left whitespace-pre-line rounded-2xl bg-white/5 border-2 border-cyan-700/50 px-5 py-5 hover:bg-white/10 transition shadow-[0_1px_0_0_rgba(255,255,255,0.05)_inset]"
              >
                <div className="mb-3 grid place-items-center">
                  <MapPin className="w-7 h-7" />
                </div>
                <div className="text-center font-extrabold text-[16px] leading-5">
                  Campus{"\n"}Locations
                </div>
              </Link>
            </div>
          </div>

          <button
            className="absolute left-4 bottom-4 h-10 w-10 rounded-full bg-white/10 grid place-items-center hover:bg-white/15 transition"
            aria-label="Settings"
            title="Settings"
          >
            <Cog className="w-5 h-5" />
          </button>
        </aside>

        {/* Main chat */}
        <main className="h-full min-w-0 rounded-lg bg-[radial-gradient(1200px_700px_at_center,#2f3744_0%,#232a36_60%,#1b1f2a_100%)] border border-white/5 overflow-hidden">
          <div className="flex flex-col h-full min-h-0">
            <div
              ref={scrollerRef}
              className="flex-1 min-h-0 overflow-y-auto px-6 py-6"
            >
              <div className="mx-auto w-full max-w-4xl space-y-4">
                {/* Active session header */}
                <div className="text-sm text-zinc-300/80">
                  <div className="font-semibold">
                    {sessions.find((s) => s.id === activeId)?.title ||
                      "New chat"}
                  </div>
                  <div>
                    {fmt(sessions.find((s) => s.id === activeId)?.createdAt)}
                  </div>
                </div>

                {messages.map((m, idx) => (
                  <div
                    key={idx}
                    className={
                      m.role === "user"
                        ? "ml-auto max-w-[80%] rounded-2xl bg-white/10 px-4 py-3"
                        : "mr-auto max-w-[90%] rounded-2xl bg-black/20 px-4 py-3"
                    }
                  >
                    <div className="whitespace-pre-wrap text-left break-words">
                      {m.role === "assistant" ? renderRich(m.text) : m.text}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="mr-auto max-w-[90%] rounded-2xl bg-black/20 px-4 py-3 text-left opacity-80">
                    Thinking…
                  </div>
                )}
                <div className="h-2" />
              </div>
            </div>

            <div className="shrink-0 px-6 pb-6">
              <div className="mx-auto w-full max-w-4xl">
                <div className="flex items-center gap-2 rounded-2xl border-2 border-cyan-700/50 bg-white/5 px-4">
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        send();
                      }
                    }}
                    disabled={loading}
                    className="flex-1 bg-transparent py-4 outline-none placeholder:text-zinc-300"
                    placeholder="Enter text here and ask anything about your university"
                  />
                  <button
                    onClick={() => send()}
                    disabled={loading}
                    className="my-2 ms-1 h-10 w-10 rounded-full grid place-items-center bg-white/15 hover:bg-white/25 disabled:opacity-50 transition"
                    title="Send"
                  >
                    <Play className="w-5 h-5" />
                  </button>
                </div>
                {errorText && (
                  <div className="mt-2 text-sm text-red-300">{errorText}</div>
                )}
              </div>
              <p className="mt-6 text-zinc-300 text-sm text-center">
                UniBot cites official UIU sources when available.
              </p>
            </div>
          </div>
        </main>
      </div>

      

      {/* History Modal */}
      {showHistory && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4">
          <div className="w-full max-w-3xl rounded-2xl bg-[#232a36] border border-white/10 shadow-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2 font-semibold">
                <HistoryIcon className="w-5 h-5" />
                Chat History
              </div>
              <button
                onClick={() => setShowHistory(false)}
                className="px-3 py-1.5 rounded-md bg-white/10 hover:bg-white/15 transition"
              >
                Close
              </button>
            </div>
            <div className="max-h-[70vh] overflow-y-auto divide-y divide-white/5">
              {sessions.map((s) => (
                <div key={s.id} className="p-4 hover:bg-white/5">
                  <div className="flex items-start gap-3">
                    <button
                      onClick={() => restoreSession(s.id)}
                      className="text-left flex-1"
                      title="Open this chat"
                    >
                      <div className="font-semibold">
                        {s.title || "New chat"}
                      </div>
                      <div className="text-xs text-zinc-300/80 mb-2">
                        {fmt(s.createdAt)}
                      </div>
                      {/* preview of text content (previous messages) */}
                      <div className="text-sm text-zinc-200/90 line-clamp-3 whitespace-pre-wrap">
                        {(s.messages || [])
                          .map((m) =>
                            m.role === "user"
                              ? `You: ${m.text}`
                              : `Bot: ${m.text}`
                          )
                          .join("\n")
                          .slice(0, 500)}
                      </div>
                    </button>
                    <button
                      onClick={() => deleteSession(s.id)}
                      className="ml-2 p-2 rounded-lg bg-red-900/40 hover:bg-red-800/50 transition"
                      title="Delete chat"
                    >
                      <Trash2 className="w-4 h-4 text-red-200" />
                    </button>
                  </div>
                </div>
              ))}
              {!sessions.length && (
                <div className="p-6 text-center text-zinc-300">
                  No history yet.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
