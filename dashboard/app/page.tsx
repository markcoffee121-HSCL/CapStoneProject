'use client';
import { useEffect, useState } from 'react';

type Health = {
  status: string;
  service: string;
  version: string;
  groq_model: string;
  search_provider: string;
};

export default function HomePage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const backend = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:9009";
    fetch(`${backend}/healthz`)
      .then((r) => r.json())
      .then(setHealth)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <main style={{ padding: 24, fontFamily: "ui-sans-serif, system-ui" }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 12 }}>
        HSCL Capstone — Monitoring Dashboard
      </h1>
      <p style={{ opacity: 0.8 }}>
        Backend connection status: <strong>{health ? "Connected ✅" : "Connecting…"}</strong>
      </p>

      {health && (
        <pre style={{ marginTop: 16, background: "#0b0f17", color: "#e6edf3",
                      padding: 16, borderRadius: 12, overflowX: "auto" }}>
{JSON.stringify(health, null, 2)}
        </pre>
      )}

      {error && (
        <pre style={{ marginTop: 16, background: "#2a0f0f", color: "#ffd6d6",
                      padding: 16, borderRadius: 12, overflowX: "auto" }}>
{error}
        </pre>
      )}

      {!health && !error && (
        <p style={{ marginTop: 16, opacity: 0.7 }}>
          Tip: ensure the backend is running on <code>http://localhost:9009</code> and set{" "}
          <code>NEXT_PUBLIC_BACKEND_URL</code> if different.
        </p>
      )}
    </main>
  );
}
