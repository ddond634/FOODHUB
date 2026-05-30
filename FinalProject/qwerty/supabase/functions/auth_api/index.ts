import { serve } from "https://deno.land/std@0.201.0/http/server.ts";
import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const JWT_SECRET = Deno.env.get("JWT_SECRET") ?? "";

const admin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
  auth: { persistSession: false },
});

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders },
  });

const b64url = (input: string) =>
  btoa(input).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");

async function signJwt(userId: number, role: string, email: string): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const header = b64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = b64url(JSON.stringify({
    user_id: userId,
    role,
    email,
    iat: now,
    exp: now + 60 * 60 * 24,
  }));
  const data = `${header}.${payload}`;
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(JWT_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data));
  const sigB64 = b64url(String.fromCharCode(...new Uint8Array(sig)));
  return `${data}.${sigB64}`;
}

function randomSalt(length = 16): string {
  const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  const bytes = crypto.getRandomValues(new Uint8Array(length));
  return Array.from(bytes, (b) => chars[b % chars.length]).join("");
}

async function hashPassword(password: string): Promise<string> {
  const iterations = 600000;
  const salt = randomSalt(16);
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(password),
    "PBKDF2",
    false,
    ["deriveBits"],
  );
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt: new TextEncoder().encode(salt), iterations, hash: "SHA-256" },
    keyMaterial,
    256,
  );
  const hex = Array.from(new Uint8Array(bits)).map((b) => b.toString(16).padStart(2, "0")).join("");
  return `pbkdf2:sha256:${iterations}$${salt}$${hex}`;
}

async function checkPasswordHash(pwhash: string, password: string): Promise<boolean> {
  if (!pwhash?.startsWith("pbkdf2:") || !password) return false;
  const parts = pwhash.split("$");
  if (parts.length !== 3) return false;

  const methodParts = parts[0].split(":");
  const iterations = parseInt(methodParts[2] ?? "600000", 10);
  const salt = parts[1];
  const storedHex = parts[2];

  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(password),
    "PBKDF2",
    false,
    ["deriveBits"],
  );
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt: new TextEncoder().encode(salt), iterations, hash: "SHA-256" },
    keyMaterial,
    256,
  );
  const hex = Array.from(new Uint8Array(bits)).map((b) => b.toString(16).padStart(2, "0")).join("");
  return hex === storedHex;
}

serve(async (req: Request) => {
  if (req.method === "OPTIONS") return json({ success: true });

  if (!JWT_SECRET) {
    return json({ success: false, error: "JWT_SECRET is not configured" }, 500);
  }

  try {
    const url = new URL(req.url);
    const segments = url.pathname.split("/").filter(Boolean);
    const action = segments.filter((p) => p !== "auth_api" && p !== "api").pop();

    if (req.method === "GET" && !action) {
      return json({
        success: true,
        message: "Hub auth API",
        endpoints: ["POST /login", "POST /register"],
      });
    }

    const body = req.method === "POST" ? await req.json().catch(() => ({})) : {};

    if (action === "login" && req.method === "POST") {
      const email = String(body.email ?? "").trim().toLowerCase();
      const password = String(body.password ?? "");
      if (!email || !password) {
        return json({ success: false, error: "Missing email or password" }, 400);
      }

      const { data: user, error } = await admin
        .from("users")
        .select("id,email,password_hash,role,first_name,last_name,is_verified")
        .eq("email", email)
        .maybeSingle();

      if (error) return json({ success: false, error: error.message }, 500);
      if (!user) return json({ success: false, error: "Invalid credentials" }, 401);

      const valid = await checkPasswordHash(String(user.password_hash ?? ""), password);
      if (!valid) return json({ success: false, error: "Invalid credentials" }, 401);

      const token = await signJwt(Number(user.id), String(user.role ?? "customer"), String(user.email));
      return json({
        success: true,
        token,
        user: {
          id: user.id,
          email: user.email,
          role: user.role,
          first_name: user.first_name,
          last_name: user.last_name,
        },
      });
    }

    if (action === "register" && req.method === "POST") {
      const email = String(body.email ?? "").trim().toLowerCase();
      const password = String(body.password ?? "");
      const role = String(body.role ?? "customer");
      const firstName = String(body.first_name ?? "").trim();
      const lastName = String(body.last_name ?? "").trim();

      if (!email || !password) {
        return json({ success: false, error: "Missing email or password" }, 400);
      }
      if (password.length < 6) {
        return json({ success: false, error: "Password must be at least 6 characters" }, 400);
      }

      const { data: existing } = await admin
        .from("users")
        .select("id")
        .eq("email", email)
        .maybeSingle();
      if (existing) return json({ success: false, error: "User already exists" }, 400);

      const passwordHash = await hashPassword(password);
      const { data: created, error } = await admin
        .from("users")
        .insert([{
          email,
          password_hash: passwordHash,
          role,
          first_name: firstName || null,
          last_name: lastName || null,
          is_verified: 1,
          created_at: new Date().toISOString(),
        }])
        .select("id,email,role,first_name,last_name")
        .single();

      if (error) return json({ success: false, error: error.message }, 400);

      const token = await signJwt(Number(created.id), String(created.role ?? "customer"), String(created.email));
      return json({
        success: true,
        token,
        user: created,
      }, 201);
    }

    return json({ success: false, error: "Not found" }, 404);
  } catch (err) {
    return json({ success: false, error: err instanceof Error ? err.message : String(err) }, 500);
  }
});
