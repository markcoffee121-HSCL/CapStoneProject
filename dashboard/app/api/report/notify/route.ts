export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const backend = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:9009";
  const body = await req.text();
  let runId: string | null = null;

  try {
    const parsed = body ? JSON.parse(body) : {};
    runId = parsed?.run_id ?? null;
  } catch {
    /* ignore; fall back to query */
  }
  if (!runId) {
    const url = new URL(req.url);
    runId = url.searchParams.get("run_id");
  }
  if (!runId) return new Response(JSON.stringify({ error: "missing_run_id" }), { status: 400 });

  const r = await fetch(`${backend}/runs/${encodeURIComponent(runId)}/notify`, { method: "POST" });
  const text = await r.text();
  return new Response(text, { status: r.status, headers: { "content-type": "application/json" } });
}
