import { serve } from "https://deno.land/std@0.201.0/http/server.ts";
import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm";
import {
  COMPLETED_ORDER_STATUSES,
  RIDER_FEE_RATE,
  calcRiderEarnings,
  roundMoney,
} from "../_shared/earnings.ts";

const admin = createClient(
  Deno.env.get("SUPABASE_URL") ?? "",
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "",
  { auth: { persistSession: false } },
);

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-hub-token",
  "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...corsHeaders } });

const ok = (body: Record<string, unknown>, status = 200) => json({ success: true, ...body }, status);
const fail = (error: string, status = 400) => json({ success: false, error }, status);

async function verifyHubToken(token: string) {
  const secret = Deno.env.get("JWT_SECRET");
  if (!secret || !token) return null;
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
    const data = new TextEncoder().encode(`${parts[0]}.${parts[1]}`);
    const signature = Uint8Array.from(atob(parts[2].replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
    if (!(await crypto.subtle.verify("HMAC", key, signature, data))) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    if (payload.exp && Date.now() / 1000 > Number(payload.exp)) return null;
    return { user_id: Number(payload.user_id), role: String(payload.role ?? "customer") };
  } catch { return null; }
}

function getHubToken(req: Request) {
  const hub = req.headers.get("x-hub-token") ?? req.headers.get("X-Hub-Token") ?? "";
  if (hub) return hub.trim();
  const auth = req.headers.get("authorization") ?? "";
  const m = auth.match(/^Bearer\s+(.+)$/i);
  if (!m) return "";
  const token = m[1].trim();
  const anon = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
  return anon && token === anon ? "" : token;
}

async function requireRider(req: Request) {
  const hub = await verifyHubToken(getHubToken(req));
  if (!hub) return { error: fail("Unauthorized", 401) };
  if (hub.role !== "rider") return { error: fail("Must be a rider", 403) };

  let { data: rider } = await admin.from("riders").select("id,user_id,availability,rider_status").eq("user_id", hub.user_id).maybeSingle();
  if (!rider) {
    const { data: created } = await admin.from("riders").insert([{
      user_id: hub.user_id,
      verified: 1,
      rider_status: "active",
      availability: "online",
    }]).select("id,user_id,availability,rider_status").single();
    rider = created;
  }
  if (!rider) return { error: fail("Rider profile not found", 404) };
  return { hub, rider };
}

async function getOrderSubtotal(orderId: number): Promise<number> {
  const { data: items } = await admin.from("order_items").select("quantity,price").eq("order_id", orderId);
  const subtotal = (items ?? []).reduce((sum, item) => sum + Number(item.quantity ?? 0) * Number(item.price ?? 0), 0);
  return roundMoney(subtotal);
}

async function enrichOrder(order: Record<string, unknown>) {
  const orderId = Number(order.id);
  const { data: items } = await admin.from("order_items").select("product_id,quantity,price").eq("order_id", orderId);
  const titles: string[] = [];
  for (const item of items ?? []) {
    const { data: product } = await admin.from("products").select("title").eq("id", item.product_id).maybeSingle();
    if (product?.title) titles.push(String(product.title));
  }
  const productSubtotal = roundMoney(
    (items ?? []).reduce((sum, item) => sum + Number(item.quantity ?? 0) * Number(item.price ?? 0), 0),
  );
  const riderEarnings = calcRiderEarnings(productSubtotal);
  return {
    ...order,
    items: titles.join(", ") || "N/A",
    items_count: titles.length,
    product_subtotal: productSubtotal,
    product_sales: productSubtotal,
    rider_earnings: riderEarnings,
    delivery_fee: riderEarnings,
  };
}

function isToday(isoDate: string | null | undefined): boolean {
  if (!isoDate) return false;
  return String(isoDate).startsWith(new Date().toISOString().slice(0, 10));
}

async function buildRiderEarningsSummary(riderId: number, start?: string | null, end?: string | null) {
  const { data: orders } = await admin
    .from("orders")
    .select("id,status,created_at,delivered_at,total")
    .eq("rider_id", riderId)
    .in("status", COMPLETED_ORDER_STATUSES)
    .order("delivered_at", { ascending: false });

  const deliveries: Record<string, unknown>[] = [];
  let totalProductSales = 0;
  let totalEarnings = 0;

  for (const order of orders ?? []) {
    const deliveredAt = String(order.delivered_at ?? order.created_at ?? "");
    if (start || end) {
      const d = new Date(deliveredAt);
      if (start && d < new Date(start)) continue;
      if (end) {
        const endDate = new Date(end);
        endDate.setHours(23, 59, 59, 999);
        if (d > endDate) continue;
      }
    }

    const subtotal = await getOrderSubtotal(Number(order.id));
    const earnings = calcRiderEarnings(subtotal);
    totalProductSales = roundMoney(totalProductSales + subtotal);
    totalEarnings = roundMoney(totalEarnings + earnings);

    deliveries.push({
      order_id: order.id,
      delivered_at: order.delivered_at ?? order.created_at,
      status: order.status,
      product_subtotal: subtotal,
      product_sales: subtotal,
      rider_earnings: earnings,
      delivery_fee: earnings,
    });
  }

  return {
    total_product_sales: totalProductSales,
    total_earnings: totalEarnings,
    net_earnings: totalEarnings,
    completed_deliveries: deliveries.length,
    rider_fee_rate: RIDER_FEE_RATE * 100,
    deliveries,
  };
}

serve(async (req) => {
  if (req.method === "OPTIONS") return json({ success: true });

  try {
    const url = new URL(req.url);
    const segments = url.pathname.split("/").filter(Boolean).filter((p) =>
      !["rider_api", "api", "rider", "riders", "orders"].includes(p)
    );

    // orders/:id/delivery-update
    const pathParts = url.pathname.split("/").filter(Boolean);
    const ordersIdx = pathParts.indexOf("orders");
    if (ordersIdx >= 0 && pathParts[ordersIdx + 2] === "delivery-update" && req.method === "PUT") {
      const auth = await requireRider(req);
      if (auth.error) return auth.error;
      const orderId = Number(pathParts[ordersIdx + 1]);
      const body = await req.json().catch(() => ({}));
      const newStatus = String(body.status ?? "");
      if (!["in-transit", "delivered", "completed"].includes(newStatus)) {
        return fail('Invalid status. Use "in-transit", "delivered", or "completed"');
      }

      const { data: order } = await admin.from("orders").select("id,rider_id,status").eq("id", orderId).maybeSingle();
      if (!order) return fail("Order not found", 404);
      if (Number(order.rider_id) !== Number(auth.rider!.id)) return fail("Not authorized for this order", 403);

      const current = String(order.status ?? "");
      if (newStatus === "in-transit" && !["dispatched", "ready", "placed"].includes(current)) {
        return fail(`Cannot move from ${current} to in-transit`);
      }
      if (newStatus === "delivered" && !["in-transit", "dispatched"].includes(current)) {
        return fail(`Cannot move from ${current} to delivered`);
      }

      const update: Record<string, unknown> = { status: newStatus };
      if (newStatus === "delivered" || newStatus === "completed") {
        update.delivered_at = new Date().toISOString();
      }
      const { error } = await admin.from("orders").update(update).eq("id", orderId);
      if (error) return fail(error.message, 400);
      return ok({ message: "Delivery status updated", order_id: orderId, status: newStatus });
    }

    const auth = await requireRider(req);
    if (auth.error) return auth.error;
    const riderId = Number(auth.rider!.id);
    const userId = auth.hub!.user_id;
    const [resource, sub] = segments;

    if (resource === "dashboard" && req.method === "GET") {
      const { data: user } = await admin.from("users").select("first_name,last_name,email,avatar_url").eq("id", userId).maybeSingle();
      const { data: activeOrders } = await admin.from("orders").select("id,status").eq("rider_id", riderId).in("status", ["dispatched", "in-transit", "ready"]);
      const { data: completedOrders } = await admin.from("orders").select("id,delivered_at,created_at").eq("rider_id", riderId).in("status", COMPLETED_ORDER_STATUSES);

      let totalEarnings = 0;
      let earningsToday = 0;
      for (const order of completedOrders ?? []) {
        const subtotal = await getOrderSubtotal(Number(order.id));
        const earnings = calcRiderEarnings(subtotal);
        totalEarnings = roundMoney(totalEarnings + earnings);
        if (isToday(String(order.delivered_at ?? order.created_at))) {
          earningsToday = roundMoney(earningsToday + earnings);
        }
      }

      return ok({
        dashboard: {
          rider_info: { ...user, ...auth.rider },
          active_deliveries: activeOrders?.length ?? 0,
          completed_deliveries: completedOrders?.length ?? 0,
          completed_today: completedOrders?.filter((o) => isToday(String(o.delivered_at ?? o.created_at))).length ?? 0,
          total_earnings: totalEarnings,
          earnings_today: earningsToday,
          average_rating: 5,
          rider_service_fee_rate: RIDER_FEE_RATE,
          rider_service_fee_percentage: RIDER_FEE_RATE * 100,
        },
      });
    }

    if (resource === "earnings" && sub === "summary" && req.method === "GET") {
      const start = url.searchParams.get("start");
      const end = url.searchParams.get("end");
      const period = url.searchParams.get("period") ?? "all";
      let rangeStart: string | null = start;
      let rangeEnd: string | null = end;
      if (period === "today") {
        rangeStart = new Date(new Date().getFullYear(), new Date().getMonth(), new Date().getDate()).toISOString();
      } else if (period === "month" || period === "monthly") {
        rangeStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString();
      }
      const summary = await buildRiderEarningsSummary(riderId, rangeStart, rangeEnd);
      return ok({ data: summary, message: "Rider earnings summary loaded" });
    }

    if (resource === "orders" && req.method === "GET") {
      const { data, error } = await admin.from("orders").select("*").eq("rider_id", riderId).order("created_at", { ascending: false });
      if (error) return fail(error.message, 500);
      const orders = await Promise.all((data ?? []).map((o) => enrichOrder(o as Record<string, unknown>)));
      return ok({ orders });
    }

    if (resource === "available-orders" && req.method === "GET") {
      const { data, error } = await admin
        .from("orders")
        .select("*")
        .in("status", ["ready", "placed", "pending"])
        .or("rider_id.is.null,rider_id.eq.0")
        .order("created_at", { ascending: true });
      if (error) return fail(error.message, 500);
      const orders = await Promise.all((data ?? []).map((o) => enrichOrder(o as Record<string, unknown>)));
      return ok({ data: orders, message: `${orders.length} available orders` });
    }

    if (resource === "accept-order" && req.method === "POST") {
      const body = await req.json().catch(() => ({}));
      const orderId = Number(body.order_id);
      if (!orderId) return fail("Order ID required");

      const { data: order } = await admin.from("orders").select("id,status,rider_id").eq("id", orderId).maybeSingle();
      if (!order) return fail("Order not found", 404);
      if (!["ready", "placed", "pending"].includes(String(order.status))) return fail("Order is not available for pickup");
      if (order.rider_id) return fail("Order already assigned", 400);

      const { error } = await admin.from("orders").update({ rider_id: riderId, status: "dispatched" }).eq("id", orderId);
      if (error) return fail(error.message, 400);
      return ok({ data: { order_id: orderId, status: "dispatched" }, message: "Order accepted" });
    }

    return fail(`Unsupported endpoint: ${resource || "root"}`, 404);
  } catch (err) {
    return fail(err instanceof Error ? err.message : String(err), 500);
  }
});
