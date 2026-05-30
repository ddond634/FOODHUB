import { serve } from "https://deno.land/std@0.201.0/http/server.ts";
import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";

const admin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
  auth: { persistSession: false },
});

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST,OPTIONS",
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders },
  });

async function broadcastChange(table: string, payload: Record<string, unknown>) {
  const channel = admin.channel("hub-updates", { config: { broadcast: { self: false } } });
  await new Promise<void>((resolve) => {
    channel.subscribe((status) => {
      if (status === "SUBSCRIBED") resolve();
    });
  });

  await channel.send({
    type: "broadcast",
    event: `${table}_changed`,
    payload,
  });

  admin.removeChannel(channel);
}

serve(async (req: Request) => {
  if (req.method === "OPTIONS") return json({ success: true });

  if (req.method !== "POST") {
    return json({ success: false, error: "Method not allowed" }, 405);
  }

  try {
    const body = await req.json().catch(() => ({}));
    const table = String(body.table ?? body.record?.table ?? "unknown");
    const eventType = String(body.type ?? "UNKNOWN");

    await broadcastChange(table, {
      type: eventType,
      table,
      record: body.record ?? null,
      old_record: body.old_record ?? null,
      at: new Date().toISOString(),
    });

    return json({ success: true, table, type: eventType });
  } catch (err) {
    return json(
      { success: false, error: err instanceof Error ? err.message : String(err) },
      500,
    );
  }
});
