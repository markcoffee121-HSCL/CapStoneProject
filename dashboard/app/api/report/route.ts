export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const backend = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:9009";
  const url = new URL(req.url);
  const runId = url.searchParams.get("run_id");
  const inline = url.searchParams.get("inline") === "1";
  if (!runId) return new Response(JSON.stringify({ error: "missing_run_id" }), { status: 400 });

  const target = `${backend}/runs/${encodeURIComponent(runId)}/report${inline ? "?inline=1" : ""}`;
  const upstream = await fetch(target, { cache: "no-store" });

  const headers = new Headers(upstream.headers);
  return new Response(upstream.body, { status: upstream.status, headers });
}
