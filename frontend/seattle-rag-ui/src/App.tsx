import { useEffect, useState } from "react";

export default function App() {
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const base = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
    fetch(`${base}/healthz`)

      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d) => { setMessage(d?.status ?? "ok"); setStatus("ok"); })
      .catch((e) => { setMessage(e.message); setStatus("error"); });
  }, []);

  return (
    <main className="min-h-dvh bg-slate-50 flex items-center justify-center">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow">
        <h1 className="text-2xl font-semibold">Seattle RAG — Frontend</h1>
        <p className="text-sm text-slate-600 mt-1">
          Tailwind v4 quick check • Try editing this file and using utility classes.
        </p>

        <div className="mt-4 rounded-xl border p-4">
          <div className="text-sm text-slate-500 mb-2">Backend health</div>
          <div
            className={
              "inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm " +
              (status === "ok"
                ? "bg-green-100 text-green-700"
                : status === "loading"
                ? "bg-yellow-100 text-yellow-700"
                : status === "error"
                ? "bg-red-100 text-red-700"
                : "bg-slate-100 text-slate-700")
            }
          >
            {status.toUpperCase()}
          </div>
          <pre className="mt-3 whitespace-pre-wrap break-words text-xs text-slate-700">
            {message || "— (disabled for now)"}
          </pre>
        </div>
      </div>
    </main>
  );
}
