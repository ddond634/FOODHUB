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
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-hub-token",
  "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
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
  if (!pwhash || !password) return false;
  if (pwhash === "supabase" || pwhash === "flask-managed") return false;
  if (!pwhash.startsWith("pbkdf2:")) return false;

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

async function authenticateWithSupabaseAuth(email: string, password: string): Promise<boolean> {
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
  if (!SUPABASE_URL || !anonKey) return false;

  const response = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: {
      apikey: anonKey,
      Authorization: `Bearer ${anonKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  return response.ok;
}

async function verifyHubToken(token: string): Promise<{ user_id: number; email?: string; role?: string } | null> {
  if (!JWT_SECRET || !token) return null;

  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;

    const key = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(JWT_SECRET),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["verify"],
    );

    const data = new TextEncoder().encode(`${parts[0]}.${parts[1]}`);
    const signature = Uint8Array.from(
      atob(parts[2].replace(/-/g, "+").replace(/_/g, "/")),
      (c) => c.charCodeAt(0),
    );
    const valid = await crypto.subtle.verify("HMAC", key, signature, data);
    if (!valid) return null;

    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    if (payload.exp && Date.now() / 1000 > Number(payload.exp)) return null;

    const userId = Number(payload.user_id);
    if (!Number.isInteger(userId) || userId <= 0) return null;
    return {
      user_id: userId,
      email: typeof payload.email === "string" ? payload.email : undefined,
      role: typeof payload.role === "string" ? payload.role : "customer",
    };
  } catch {
    return null;
  }
}

function getHubTokenFromRequest(req: Request): string {
  const hubHeader = req.headers.get("x-hub-token") ?? req.headers.get("X-Hub-Token") ?? "";
  if (hubHeader) return hubHeader.trim();

  const auth = req.headers.get("authorization") ?? "";
  const match = auth.match(/^Bearer\s+(.+)$/i);
  if (!match) return "";
  const token = match[1].trim();
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
  if (anonKey && token === anonKey) return "";
  return token;
}

const USER_FIELDS = new Set([
  "first_name", "middle_name", "last_name", "suffix", "email", "phone", "avatar_url",
  "gender", "birthdate", "address_line1", "address_line2", "city", "province", "region", "postal_code",
]);

async function resolveUserAfterAuth(email: string, password: string, role?: string, firstName?: string, lastName?: string) {
  const { data: user, error } = await admin
    .from("users")
    .select("id,email,password_hash,role,first_name,last_name,is_verified")
    .eq("email", email)
    .maybeSingle();

  if (error) throw new Error(error.message);
  if (user) return user;

  const passwordHash = await hashPassword(password);
  const { data: created, error: insertError } = await admin
    .from("users")
    .insert([{
      email,
      password_hash: passwordHash,
      role: role ?? "customer",
      first_name: firstName || null,
      last_name: lastName || null,
      is_verified: 1,
      created_at: new Date().toISOString(),
    }])
    .select("id,email,password_hash,role,first_name,last_name,is_verified")
    .single();

  if (insertError) throw new Error(insertError.message);
  return created;
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

    const body = req.method === "POST" || req.method === "PUT"
      ? await req.json().catch(() => ({}))
      : {};

    if (action === "me" && req.method === "GET") {
      const hubUser = await verifyHubToken(getHubTokenFromRequest(req));
      if (!hubUser) return json({ success: false, error: "Unauthorized" }, 401);

      const { data: user, error } = await admin
        .from("users")
        .select("*")
        .eq("id", hubUser.user_id)
        .maybeSingle();
      if (error) return json({ success: false, error: error.message }, 500);
      if (!user) return json({ success: false, error: "User not found" }, 404);

      const profile: Record<string, unknown> = { ...user };
      delete profile.password_hash;
      delete profile.otp_code;

      const role = String(hubUser.role ?? user.role ?? "customer");
      if (role === "seller") {
        const { data: seller } = await admin.from("sellers").select("*").eq("user_id", hubUser.user_id).maybeSingle();
        if (seller) profile.seller = seller;
      } else if (role === "rider") {
        const { data: rider } = await admin.from("riders").select("*").eq("user_id", hubUser.user_id).maybeSingle();
        if (rider) profile.rider = rider;
      }

      return json({ success: true, data: profile });
    }

    if (action === "me" && req.method === "PUT") {
      const hubUser = await verifyHubToken(getHubTokenFromRequest(req));
      if (!hubUser) return json({ success: false, error: "Unauthorized" }, 401);
      if (!body || typeof body !== "object" || !Object.keys(body).length) {
        return json({ success: false, error: "No data provided for update" }, 400);
      }

      const updates: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(body as Record<string, unknown>)) {
        if (USER_FIELDS.has(key)) updates[key] = value;
      }
      if (!Object.keys(updates).length) {
        return json({ success: false, error: "No valid fields to update" }, 400);
      }

      const { data: updated, error } = await admin
        .from("users")
        .update(updates)
        .eq("id", hubUser.user_id)
        .select("*")
        .single();
      if (error) return json({ success: false, error: error.message }, 400);

      const profile: Record<string, unknown> = { ...updated };
      delete profile.password_hash;
      delete profile.otp_code;
      return json({ success: true, data: profile });
    }

    if (action === "login" && req.method === "POST") {
      const email = String(body.email ?? "").trim().toLowerCase();
      const password = String(body.password ?? "");
      if (!email || !password) {
        return json({ success: false, error: "Missing email or password" }, 400);
      }

      let user = await admin
        .from("users")
        .select("id,email,password_hash,role,first_name,last_name,is_verified")
        .eq("email", email)
        .maybeSingle()
        .then(({ data, error }) => {
          if (error) throw new Error(error.message);
          return data;
        });

      let authenticated = false;

      if (user) {
        authenticated = await checkPasswordHash(String(user.password_hash ?? ""), password);
      }

      if (!authenticated) {
        authenticated = await authenticateWithSupabaseAuth(email, password);
        if (authenticated && !user) {
          user = await resolveUserAfterAuth(email, password);
        } else if (authenticated && user) {
          const passwordHash = await hashPassword(password);
          await admin.from("users").update({ password_hash: passwordHash }).eq("id", user.id);
        }
      }

      if (!authenticated) {
        return json({ success: false, error: "Invalid credentials" }, 401);
      }

      if (!user) {
        return json({ success: false, error: "Invalid credentials" }, 401);
      }

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

      // Create Supabase Auth user so password login works across web + mobile
      const anonKey = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
      if (SUPABASE_URL && anonKey) {
        await fetch(`${SUPABASE_URL}/auth/v1/signup`, {
          method: "POST",
          headers: {
            apikey: anonKey,
            Authorization: `Bearer ${anonKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email, password }),
        }).catch(() => null);
      }

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
