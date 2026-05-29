import { serve } from "https://deno.land/std@0.201.0/http/server.ts";
import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm';

const SUPABASE_URL = Deno.env.get('SUPABASE_URL');
const SUPABASE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || Deno.env.get('SUPABASE_ANON_KEY');

if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.warn('SUPABASE_URL or SUPABASE_KEY not set in function environment');
}

const supabase = createClient(SUPABASE_URL ?? '', SUPABASE_KEY ?? '');

serve(async (req: Request) => {
  try {
    if (req.method !== 'GET') return new Response('Method Not Allowed', { status: 405 });

    const { data, error } = await supabase.from('users').select('*').limit(100);
    if (error) return new Response(JSON.stringify({ error: error.message }), { status: 500 });

    return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
  } catch (err) {
    return new Response(JSON.stringify({ error: String(err) }), { status: 500 });
  }
});
