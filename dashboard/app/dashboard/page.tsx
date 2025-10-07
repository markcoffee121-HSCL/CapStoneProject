'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type RunCreated = { run_id: string };
type RunStatus = {
  run_id: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
  topic?: string;
};
type RunEvent = {
  event_id: string;
  run_id: string;
  step: string;
  agent?: string | null;
  status: 'started' | 'progress' | 'completed' | 'error';
  message?: string | null;
  ts: string;
  duration_ms?: number | null;
  data?: Record<string, any> | null;
};

const card: React.CSSProperties = {
  background: '#0b0f17',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 12,
  padding: 16,
  overflow: 'hidden',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  maxWidth: '100%',
  padding: 10,
  borderRadius: 8,
  background: '#0a0a0a',
  color: '#e6edf3',
  border: '1px solid #1f2937',
  boxSizing: 'border-box',
};

function prettyTs(ts?: string) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleTimeString();
}

function Badge({ text }: { text: string }) {
  return (
    <span
      style={{
        background: '#111827',
        border: '1px solid rgba(255,255,255,0.08)',
        padding: '2px 8px',
        fontSize: 12,
        borderRadius: 999,
        whiteSpace: 'nowrap',
      }}
    >
      {text}
    </span>
  );
}

// Match backend DEPTH_PRESETS
const DEPTH_DEFAULTS = {
  quick: 3,
  standard: 6,
  deep: 10,
} as const;

type Depth = keyof typeof DEPTH_DEFAULTS;

export default function DashboardPage() {
  const backend = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:9009';

  const [topic, setTopic] = useState<string>('why does a boomerang get back to the thrower?');
  const [depth, setDepth] = useState<Depth>('quick');
  const [maxSources, setMaxSources] = useState<number>(DEPTH_DEFAULTS.quick);
  const [domains, setDomains] = useState<string>('');
  const [userModifiedSources, setUserModifiedSources] = useState<boolean>(false);
  
  const [runId, setRunId] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunStatus[]>([]);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const esRef = useRef<EventSource | null>(null);

  const [metrics, setMetrics] = useState<string>('');
  const [parsed, setParsed] = useState<Record<string, number>>({});
  
  // Auto-update maxSources when depth changes (unless user manually changed it)
  useEffect(() => {
    if (!userModifiedSources) {
      setMaxSources(DEPTH_DEFAULTS[depth]);
    }
  }, [depth, userModifiedSources]);

  const fetchRuns = useCallback(async () => {
    try {
      const r = await fetch(`${backend}/runs`, { cache: 'no-store' });
      const j = await r.json();
      setRuns(Array.isArray(j) ? j : []);
    } catch {
      // ignore
    }
  }, [backend]);

  const startRun = useCallback(async () => {
    const body: any = { topic, depth, max_sources: maxSources };
    const d = domains
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (d.length) body.domains = d;

    const r = await fetch(`${backend}/research`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    const j: RunCreated = await r.json();

    setRunId(j.run_id);
    setEvents([]);
    const prev = JSON.parse(localStorage.getItem('hscl_recent_runs') || '[]');
    localStorage.setItem('hscl_recent_runs', JSON.stringify([j.run_id, ...prev].slice(0, 10)));
    fetchRuns();
  }, [backend, topic, depth, maxSources, domains, fetchRuns]);

  // Open SSE for selected run
  useEffect(() => {
    if (!runId) return;

    esRef.current?.close();
    const es = new EventSource(`${backend}/events?run_id=${encodeURIComponent(runId)}`);
    esRef.current = es;


    const onEvent = (e: MessageEvent) => {
  
  // Split by newlines in case multiple events come together
  const lines = e.data.split('\n').filter((line: string) => line.trim());
  
  for (const line of lines) {
    try {
      const data = JSON.parse(line) as RunEvent;
      
      // Skip the "hello" connection message
      if (!data.event_id) continue;
      
      setEvents((prev) => {
        const newEvents = [...prev, data];
        return newEvents;
      });
    } catch (error) {
    }
  }
};
    es.addEventListener('run_event', onEvent as any);
    es.onerror = (error) => {
};
    return () => {

      es.removeEventListener('run_event', onEvent as any);
      es.close();
    };
  }, [backend, runId]);

  // Poll metrics
  useEffect(() => {
    let alive = true;
    const grab = async () => {
      try {
        const r = await fetch(`${backend}/metrics`, { cache: 'no-store' });
        const t = await r.text();
        if (alive) setMetrics(t);
      } catch {
        // ignore
      }
    };
    grab();
    const id = setInterval(grab, 10_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [backend]);

  // Poll runs list every 8s
  useEffect(() => {
    fetchRuns();
    const id = setInterval(fetchRuns, 8000);
    return () => clearInterval(id);
  }, [fetchRuns]);

  // Parse Prometheus text
  useEffect(() => {
    if (!metrics) return;
    const out: Record<string, number> = {};
    const lines = metrics.split('\n');
    const httpRe = /^http_requests_total\{([^}]*)\}\s+([0-9.eE+-]+)$/;
    const groqReq = /^groq_requests_total\{([^}]*)\}\s+([0-9.eE+-]+)$/;
    const groqTok = /^groq_tokens_total\{([^}]*)\}\s+([0-9.eE+-]+)$/;
    const wReq = /^webhook_requests_total\{([^}]*)\}\s+([0-9.eE+-]+)$/;
    const wErr = /^webhook_errors_total\{([^}]*)\}\s+([0-9.eE+-]+)$/;
    const parseLabels = (s: string) =>
      Object.fromEntries(
        s.split(',').map((kv) => {
          const [k, v] = kv.split('=');
          return [k, v.replace(/^"|"$/g, '')];
        }),
      );
    for (const ln of lines) {
      let m = ln.match(httpRe);
      if (m) {
        const L = parseLabels(m[1]);
        const k = `http:${L.status || 'code'}:${L.handler || ''}`;
        out[k] = (out[k] || 0) + Number(m[2]);
        continue;
      }
      m = ln.match(groqReq);
      if (m) {
        const L = parseLabels(m[1]);
        const k = `groq:req:${L.agent || 'all'}`;
        out[k] = (out[k] || 0) + Number(m[2]);
        continue;
      }
      m = ln.match(groqTok);
      if (m) {
        const L = parseLabels(m[1]);
        const k = `groq:${L.type || 'tok'}:${L.agent || 'all'}`;
        out[k] = (out[k] || 0) + Number(m[2]);
        continue;
      }
      m = ln.match(wReq);
      if (m) {
        const L = parseLabels(m[1]);
        out[`webhook:req:${L.service}`] = (out[`webhook:req:${L.service}`] || 0) + Number(m[2]);
        continue;
      }
      m = ln.match(wErr);
      if (m) {
        const L = parseLabels(m[1]);
        out[`webhook:err:${L.service}`] = (out[`webhook:err:${L.service}`] || 0) + Number(m[2]);
        continue;
      }
    }
    setParsed(out);
  }, [metrics]);

  const steps = useMemo(() => {
    const map = new Map<string, RunEvent[]>();
    for (const e of events) {
      if (!map.has(e.step)) map.set(e.step, []);
      map.get(e.step)!.push(e);
    }
    const order = ['plan', 'search', 'retrieve', 'summarize', 'synthesize', 'critique', 'present', 'run'];
    return order
      .filter((s) => map.has(s))
      .map((s) => {
        const arr = map.get(s)!;
        const last = arr[arr.length - 1];
        return { step: s, events: arr, last };
      });
  }, [events]);

  const httpSummary = Object.entries(parsed).filter(([k]) => k.startsWith('http:')).sort();
  const groqSummary = Object.entries(parsed).filter(([k]) => k.startsWith('groq:')).sort();

  return (
    <main style={{ padding: 24, fontFamily: 'ui-sans-serif, system-ui', maxWidth: 1100, margin: '0 auto' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 12 }}>Live Monitoring Dashboard</h1>

      <section style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 16, alignItems: 'start' }}>
        <div style={card}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Start a Research Run</h2>
          <div style={{ display: 'grid', gap: 8 }}>
            <label>
              <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 4 }}>Topic</div>
              <input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="What do you want to research?"
                style={inputStyle}
              />
            </label>

            <div style={{ display: 'flex', gap: 8 }}>
              <label style={{ flex: 1 }}>
                <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 4 }}>Depth</div>
                <select
                  value={depth}
                  onChange={(e) => {
                    const newDepth = e.target.value as Depth;
                    setDepth(newDepth);
                    setUserModifiedSources(false); // Reset flag when depth changes
                  }}
                  style={inputStyle as any}
                >
                  <option value="quick">quick (3 sources)</option>
                  <option value="standard">standard (6 sources)</option>
                  <option value="deep">deep (10 sources)</option>
                </select>
              </label>

              <label style={{ width: 140 }}>
                <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 4 }}>Max Sources</div>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={maxSources}
                  onChange={(e) => {
                    setMaxSources(Number(e.target.value));
                    setUserModifiedSources(true); // Mark as user-modified
                  }}
                  style={inputStyle}
                />
              </label>
            </div>

            <label>
              <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 4 }}>Restrict to domains (comma-separated)</div>
              <input
                value={domains}
                onChange={(e) => setDomains(e.target.value)}
                placeholder="arxiv.org, nature.com"
                style={inputStyle}
              />
            </label>

            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 8, flexWrap: 'wrap' }}>
              <button
                onClick={startRun}
                style={{
                  background: '#2563eb',
                  color: 'white',
                  padding: '10px 14px',
                  borderRadius: 10,
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                Start Run
              </button>
              {runId && <Badge text={`run: ${runId.slice(0, 8)}…`} />}
            </div>
          </div>
        </div>

        <div style={card}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Recent Runs</h2>
          <button
            onClick={fetchRuns}
            style={{
              marginBottom: 8,
              background: '#111827',
              border: '1px solid #1f2937',
              color: '#e6edf3',
              borderRadius: 8,
              padding: '6px 10px',
              cursor: 'pointer',
            }}
          >
            Refresh
          </button>

          <div style={{ display: 'grid', gap: 8 }}>
            {runs.slice(0, 8).map((r) => (
              <div key={r.run_id} style={{ padding: 10, borderRadius: 8, background: '#0a0a0a', border: '1px solid #1f2937' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontWeight: 600 }}>{r.run_id.slice(0, 8)}…</div>
                  <Badge text={r.status} />
                </div>

                <div
                  style={{
                    fontSize: 12,
                    opacity: 0.85,
                    marginTop: 4,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {r.topic || '(no topic)'}
                </div>

                <div style={{ fontSize: 12, opacity: 0.8, marginTop: 4 }}>
                  created {prettyTs(r.created_at)} {r.started_at ? `• started ${prettyTs(r.started_at)}` : ''}{' '}
                  {r.finished_at ? `• finished ${prettyTs(r.finished_at)}` : ''}
                </div>

                <div style={{ marginTop: 6, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button
                    onClick={() => setRunId(r.run_id)}
                    style={{
                      background: '#0b0f17',
                      border: '1px solid #1f2937',
                      color: '#e6edf3',
                      borderRadius: 8,
                      padding: '6px 10px',
                      fontSize: 12,
                      cursor: 'pointer',
                    }}
                  >
                    Follow stream
                  </button>

                  <a
                    href={`${backend}/runs/${r.run_id}/report`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      background: '#059669',
                      border: '1px solid #0b4f3e',
                      color: 'white',
                      borderRadius: 8,
                      padding: '6px 10px',
                      fontSize: 12,
                      textDecoration: 'none',
                      display: 'inline-block',
                    }}
                  >
                    Download
                  </a>

                  <button
                    onClick={async () => {
                      const res = await fetch(`${backend}/runs/${r.run_id}/notify`, { method: 'POST' });
                      if (!res.ok) alert('Notify failed');
                      else alert('Sent to n8n');
                    }}
                    style={{
                      background: '#d97706',
                      border: '1px solid #9a5a05',
                      color: 'white',
                      borderRadius: 8,
                      padding: '6px 10px',
                      fontSize: 12,
                      cursor: 'pointer',
                    }}
                  >
                    Resend to n8n
                  </button>
                </div>
              </div>
            ))}

            {!runs.length && <div style={{ opacity: 0.7, fontSize: 14 }}>No runs yet.</div>}
          </div>
        </div>
      </section>

      <section style={{ marginTop: 16, ...card }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Live Timeline</h2>
        {!runId && <div style={{ opacity: 0.7 }}>Start a run to begin streaming events.</div>}
        {runId && events.length === 0 && <div style={{ opacity: 0.7 }}>Waiting for first event…</div>}
        {events.length > 0 && (
          <div style={{ display: 'grid', gap: 10 }}>
            {steps.map((grp) => (
              <div key={grp.step} style={{ padding: 10, borderRadius: 8, background: '#0a0a0a', border: '1px solid #1f2937' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>{grp.step}</div>
                  <Badge text={grp.last.status} />
                </div>
                <div style={{ fontSize: 12, opacity: 0.8, marginTop: 6 }}>
                  {grp.events.map((e) => (
                    <div key={e.event_id} style={{ marginBottom: 2 }}>
                      <span style={{ opacity: 0.7 }}>{prettyTs(e.ts)}</span> — <code style={{ opacity: 0.95 }}>{e.agent || 'orchestrator'}</code> → {e.status}
                      {e.message ? ` • ${e.message}` : ''}{' '}
                      {e.data && Object.keys(e.data).length ? <span style={{ opacity: 0.9 }}> • {JSON.stringify(e.data)}</span> : null}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section style={{ marginTop: 16, ...card }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Metrics Snapshot</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <h3 style={{ fontSize: 14, opacity: 0.8, marginBottom: 6 }}>HTTP</h3>
            {httpSummary.length === 0 && <div style={{ opacity: 0.7 }}>No data yet.</div>}
            {httpSummary.map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                <span>{k.replace('http:', '')}</span>
                <span>{v}</span>
              </div>
            ))}
          </div>
          <div>
            <h3 style={{ fontSize: 14, opacity: 0.8, marginBottom: 6 }}>Groq</h3>
            {groqSummary.length === 0 && <div style={{ opacity: 0.7 }}>No data yet (or GROQ_API_KEY not set).</div>}
            {groqSummary.map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                <span>{k.replace('groq:', '')}</span>
                <span>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
