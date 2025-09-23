import { useEffect, useMemo, useRef, useState } from "react";

type Role = "user" | "assistant";
type Citation = { index: number; source?: string; page?: number | string };
type Message = { role: Role; content: string; citations?: Citation[] };
type Session = { id: string; title: string; messages: Message[] };

function newId() {
  return Math.random().toString(36).slice(2, 10);
}

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([
    { id: newId(), title: "New chat", messages: [{ role: "assistant", content: "Hi! Ask me about the docs." }] },
  ]);
  const [activeId, setActiveId] = useState<string>(sessions[0].id);
  const active = useMemo(() => sessions.find(s => s.id === activeId)!, [sessions, activeId]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => inputRef.current?.focus(), [activeId]);
  useEffect(() => scrollerRef.current?.scrollTo({ top: scrollerRef.current.scrollHeight, behavior: "smooth" }), [active]);

  function createSession() {
    const s: Session = { id: newId(), title: "New chat", messages: [{ role: "assistant", content: "New chat started." }] };
    setSessions(prev => [s, ...prev]);
    setActiveId(s.id);
  }

  function renameActive(title: string) {
    setSessions(prev => prev.map(s => s.id === activeId ? { ...s, title } : s));
  }

  async function send() {
    const text = input.trim();
    if (!text || loading) return;

    // optimistic UI
    setSessions(prev => prev.map(s =>
      s.id === activeId ? { ...s, messages: [...s.messages, { role: "user", content: text }] } : s
    ));
    setInput("");
    setLoading(true);

    try {
      const base = import.meta.env.VITE_API_URL || "";
      // include history in the request so backend can ground on it
      const history = sessions.find(s => s.id === activeId)?.messages || [];
      const res = await fetch(`${base}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text, top_k: 4, history }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      setSessions(prev => prev.map(s =>
        s.id === activeId
          ? {
              ...s,
              // set title from first user message
              title: s.title === "New chat" ? text.slice(0, 40) : s.title,
              messages: [
                ...s.messages,
                { role: "assistant", content: data?.answer ?? "[no response]", citations: data?.citations || [] },
              ],
            }
          : s
      ));
    } catch (err: any) {
      setSessions(prev => prev.map(s =>
        s.id === activeId
          ? { ...s, messages: [...s.messages, { role: "assistant", content: `Error: ${err?.message || "Request failed"}` }] }
          : s
      ));
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <main className="min-h-dvh bg-slate-50 flex">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-white hidden md:flex md:flex-col">
        <div className="p-3 border-b flex items-center justify-between">
          <span className="font-semibold">Sessions</span>
          <button onClick={createSession} className="rounded-lg bg-blue-600 text-white px-2 py-1 text-sm hover:bg-blue-700">
            + New
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.map(s => (
            <button
              key={s.id}
              onClick={() => setActiveId(s.id)}
              className={
                "w-full text-left rounded-lg px-3 py-2 hover:bg-slate-100 " +
                (s.id === activeId ? "bg-slate-100 font-medium" : "")
              }
              title={s.title}
            >
              {s.title || "Untitled"}
            </button>
          ))}
        </div>
      </aside>

      {/* Chat area */}
      <section className="flex-1 mx-auto max-w-4xl px-4 py-4">
        <header className="mb-3">
          <input
            value={active.title}
            onChange={(e) => renameActive(e.target.value)}
            className="text-2xl font-semibold bg-transparent outline-none border-b focus:border-blue-500"
          />
          <p className="text-sm text-slate-600">Ask a question and I’ll search the knowledge base.</p>
        </header>

        <div className="h-[70vh] rounded-2xl border bg-white shadow flex flex-col">
          {/* messages */}
          <div ref={scrollerRef} className="flex-1 overflow-y-auto p-4 space-y-3">
            {active.messages.map((m, i) => (
              <MessageBubble key={i} role={m.role} msg={m} />
            ))}
            {loading && <TypingBubble />}
          </div>

          {/* composer */}
          <div className="border-t p-3">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Type your message… (Enter to send, Shift+Enter for newline)"
                rows={1}
                className="min-h-[44px] max-h-40 flex-1 resize-y rounded-xl border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={send}
                disabled={loading || !input.trim()}
                className="h-[44px] shrink-0 rounded-xl bg-blue-600 px-4 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? "Sending…" : "Send"}
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function MessageBubble({ role, msg }: { role: Role; msg: Message }) {
  const mine = role === "user";
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div
        className={[
          "max-w-[85%] rounded-2xl px-3 py-2 whitespace-pre-wrap break-words",
          mine ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-900",
        ].join(" ")}
      >
        {mine ? msg.content : <Assistant text={msg.content} citations={msg.citations || []} />}
      </div>
    </div>
  );
}

function Assistant({ text, citations }: { text: string; citations: Citation[] }) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <>
      <p>
        {parts.map((p, i) => {
          const m = p.match(/^\[(\d+)\]$/);
          if (!m) return <span key={i}>{p}</span>;
          const n = Number(m[1]);
          return (
            <a key={i} href={`#cite-${n}`} className="align-super text-xs underline">
              [{n}]
            </a>
          );
        })}
      </p>
      {citations.length > 0 && (
        <ul className="mt-2 text-xs text-slate-600 list-disc pl-4">
          {citations.map((c) => (
            <li key={c.index} id={`cite-${c.index}`}>
              <span className="font-mono">[{c.index}]</span>{" "}
              {c.source || "unknown source"}{c.page !== undefined ? ` (p. ${c.page})` : ""}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function TypingBubble() {
  return (
    <div className="flex justify-start">
      <div className="rounded-2xl bg-slate-100 px-3 py-2 text-slate-600">
        <span className="inline-flex items-center gap-2">
          Thinking
          <span className="inline-block w-1 h-1 rounded-full bg-slate-500 animate-bounce [animation-delay:-0.3s]" />
          <span className="inline-block w-1 h-1 rounded-full bg-slate-500 animate-bounce [animation-delay:-0.15s]" />
          <span className="inline-block w-1 h-1 rounded-full bg-slate-500 animate-bounce" />
        </span>
      </div>
    </div>
  );
}
