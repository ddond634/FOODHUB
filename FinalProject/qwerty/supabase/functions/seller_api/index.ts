import { serve } from "https://deno.land/std@0.201.0/http/server.ts";
import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm";
import {
  ACTIVE_ORDER_STATUSES,
  COMPLETED_ORDER_STATUSES,
  PLATFORM_COMMISSION_RATE,
  RIDER_FEE_RATE,
  calcSellerBreakdown,
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
  "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...corsHeaders } });

const ok = (data: unknown, message?: string, status = 200) =>
  json({ success: true, data, message, timestamp: new Date().toISOString() }, status);

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
    return { user_id: Number(payload.user_id), role: String(payload.role ?? "customer"), email: payload.email as string | undefined };
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

async function requireSeller(req: Request) {
  const hub = await verifyHubToken(getHubToken(req));
  if (!hub) return { error: fail("Unauthorized", 401) };
  if (hub.role !== "seller") return { error: fail("Must be a seller", 403) };

  const { data: seller } = await admin.from("sellers").select("id,user_id,verified,shop_status,business_name,store_name").eq("user_id", hub.user_id).maybeSingle();
  if (!seller) return { error: fail("Seller profile not found", 404) };
  if (!seller.verified) return { error: fail("Seller account pending approval", 403) };
  if (seller.shop_status !== "active") return { error: fail("Shop is not active", 403) };
  return { hub, seller };
}

async function listProducts(userId: number) {
  const { data, error } = await admin.from("products").select("*").eq("seller_id", userId).order("created_at", { ascending: false });
  if (error) throw new Error(error.message);
  return data ?? [];
}

type SellerLineItem = {
  order_id: number;
  order_status: string;
  order_date: string;
  product_id: number;
  product_title: string;
  quantity: number;
  unit_price: number;
  line_total: number;
};

async function fetchSellerLineItems(sellerUserId: number): Promise<SellerLineItem[]> {
  const { data: products } = await admin.from("products").select("id,title").eq("seller_id", sellerUserId);
  const productIds = (products ?? []).map((p) => p.id);
  if (!productIds.length) return [];

  const titleById = new Map((products ?? []).map((p) => [p.id, p.title]));

  const { data: items, error } = await admin
    .from("order_items")
    .select("order_id,product_id,quantity,price,orders(id,status,created_at,total)")
    .in("product_id", productIds);

  if (error) throw new Error(error.message);

  const rows: SellerLineItem[] = [];
  for (const item of items ?? []) {
    const order = item.orders as { id: number; status: string; created_at: string; total: number } | null;
    if (!order) continue;
    const qty = Number(item.quantity ?? 0);
    const price = Number(item.price ?? 0);
    rows.push({
      order_id: Number(item.order_id),
      order_status: String(order.status ?? ""),
      order_date: String(order.created_at ?? ""),
      product_id: Number(item.product_id),
      product_title: String(titleById.get(item.product_id) ?? "Product"),
      quantity: qty,
      unit_price: price,
      line_total: roundMoney(qty * price),
    });
  }
  return rows;
}

function inDateRange(isoDate: string, start?: string | null, end?: string | null): boolean {
  if (!isoDate) return false;
  const d = new Date(isoDate);
  if (start) {
    const s = new Date(start);
    s.setHours(0, 0, 0, 0);
    if (d < s) return false;
  }
  if (end) {
    const e = new Date(end);
    e.setHours(23, 59, 59, 999);
    if (d > e) return false;
  }
  return true;
}

function aggregateSellerOrders(items: SellerLineItem[], start?: string | null, end?: string | null) {
  const filtered = items.filter((i) => inDateRange(i.order_date, start, end));
  const byOrder = new Map<number, { status: string; date: string; gross: number; items: SellerLineItem[] }>();

  for (const item of filtered) {
    const existing = byOrder.get(item.order_id) ?? { status: item.order_status, date: item.order_date, gross: 0, items: [] };
    existing.gross = roundMoney(existing.gross + item.line_total);
    existing.items.push(item);
    byOrder.set(item.order_id, existing);
  }

  let grossRevenue = 0;
  let riderFees = 0;
  let platformCommission = 0;
  let netProfit = 0;
  let completedOrders = 0;
  let pendingOrders = 0;
  const transactions: Record<string, unknown>[] = [];

  for (const [orderId, order] of byOrder) {
    const breakdown = calcSellerBreakdown(order.gross);
    grossRevenue = roundMoney(grossRevenue + breakdown.gross_sales);
    riderFees = roundMoney(riderFees + breakdown.rider_fee);
    platformCommission = roundMoney(platformCommission + breakdown.platform_commission);
    netProfit = roundMoney(netProfit + breakdown.net_profit);

    const status = order.status.toLowerCase();
    if (COMPLETED_ORDER_STATUSES.includes(status)) completedOrders += 1;
    if (ACTIVE_ORDER_STATUSES.includes(status)) pendingOrders += 1;

    transactions.push({
      order_id: orderId,
      order_date: order.date,
      status: order.status,
      gross_sales: breakdown.gross_sales,
      rider_fee: breakdown.rider_fee,
      platform_commission: breakdown.platform_commission,
      net_profit: breakdown.net_profit,
      items_count: order.items.length,
    });
  }

  transactions.sort((a, b) => new Date(String(b.order_date)).getTime() - new Date(String(a.order_date)).getTime());

  return {
    gross_revenue: grossRevenue,
    rider_fees: riderFees,
    platform_commission: platformCommission,
    total_earnings: netProfit,
    net_profit: netProfit,
    completed_orders: completedOrders,
    pending_orders: pendingOrders,
    total_orders: byOrder.size,
    transactions,
  };
}

async function buildDashboard(sellerUserId: number, seller: Record<string, unknown>) {
  const items = await fetchSellerLineItems(sellerUserId);
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();

  const allTime = aggregateSellerOrders(items);
  const today = aggregateSellerOrders(items, todayStart);
  const month = aggregateSellerOrders(items, monthStart);

  const { count: productsCount } = await admin
    .from("products")
    .select("id", { count: "exact", head: true })
    .eq("seller_id", sellerUserId);

  return {
    business_name: seller.business_name ?? seller.store_name ?? "My Store",
    verified: seller.verified,
    products_count: productsCount ?? 0,
    total_orders: allTime.total_orders,
    pending_orders: allTime.pending_orders,
    completed_orders: allTime.completed_orders,
    total_revenue: allTime.gross_revenue,
    gross_sales: allTime.gross_revenue,
    net_profit: allTime.net_profit,
    rider_fees: allTime.rider_fees,
    platform_commission: allTime.platform_commission,
    sales_today: today.gross_revenue,
    net_profit_today: today.net_profit,
    sales_month: month.gross_revenue,
    net_profit_month: month.net_profit,
    avg_rating: 4.5,
    commission_rate: PLATFORM_COMMISSION_RATE * 100,
    rider_fee_rate: RIDER_FEE_RATE * 100,
  };
}

serve(async (req) => {
  if (req.method === "OPTIONS") return json({ success: true });

  try {
    const auth = await requireSeller(req);
    if (auth.error) return auth.error;
    const userId = auth.hub!.user_id;
    const seller = auth.seller!;

    const url = new URL(req.url);
    const segments = url.pathname.split("/").filter(Boolean).filter((p) => p !== "seller_api" && p !== "api" && p !== "sellers");
    const [resource, idStr, action] = segments;

    if (resource === "dashboard" && req.method === "GET") {
      const dashboard = await buildDashboard(userId, seller);
      return ok(dashboard, "Dashboard loaded");
    }

    if (resource === "earnings" && idStr === "summary" && req.method === "GET") {
      const period = url.searchParams.get("period") ?? "all";
      const start = url.searchParams.get("start");
      const end = url.searchParams.get("end");

      let rangeStart: string | null = start;
      let rangeEnd: string | null = end;

      if (period === "today") {
        const now = new Date();
        rangeStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
      } else if (period === "month" || period === "monthly") {
        const now = new Date();
        rangeStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
      }

      const items = await fetchSellerLineItems(userId);
      const summary = aggregateSellerOrders(items, rangeStart, rangeEnd);

      return ok({
        ...summary,
        commission_rate: PLATFORM_COMMISSION_RATE * 100,
        rider_fee_rate: RIDER_FEE_RATE * 100,
        pending_payout: roundMoney(summary.net_profit * 0.9),
        paid_out: roundMoney(summary.net_profit * 0.1),
        period,
      }, "Earnings summary loaded");
    }

    if (resource === "earnings" && idStr === "transactions" && req.method === "GET") {
      const start = url.searchParams.get("start");
      const end = url.searchParams.get("end");
      const items = await fetchSellerLineItems(userId);
      const summary = aggregateSellerOrders(items, start, end);
      return ok(summary.transactions, "Earnings transactions loaded");
    }

    if (resource !== "products") return fail(`Unsupported endpoint: ${resource || "root"}`, 404);

    const productId = idStr ? Number(idStr) : null;

    if (req.method === "GET" && !productId) {
      const products = await listProducts(userId);
      return ok(products, `${products.length} products fetched`);
    }

    if (req.method === "GET" && productId) {
      const { data, error } = await admin.from("products").select("*").eq("id", productId).eq("seller_id", userId).maybeSingle();
      if (error) return fail(error.message, 500);
      if (!data) return fail("Product not found", 404);
      return ok(data);
    }

    if (req.method === "POST" && !productId) {
      const body = await req.json().catch(() => ({}));
      if (!body.title || body.price === undefined || body.stock === undefined) {
        return fail("Required fields: title, price, stock");
      }
      const row = {
        title: String(body.title),
        description: String(body.description ?? ""),
        price: Number(body.price),
        stock: Number(body.stock),
        category: String(body.category ?? "General"),
        img_url: body.img_url ? String(body.img_url) : null,
        seller_id: userId,
        created_at: new Date().toISOString(),
      };
      const { data, error } = await admin.from("products").insert([row]).select("id").single();
      if (error) return fail(error.message, 400);
      return ok({ product_id: data.id }, "Product created", 201);
    }

    if (req.method === "PUT" && productId) {
      const body = await req.json().catch(() => ({}));
      const { data: existing } = await admin.from("products").select("id").eq("id", productId).eq("seller_id", userId).maybeSingle();
      if (!existing) return fail("Product not found", 404);

      const updates: Record<string, unknown> = {};
      for (const key of ["title", "description", "category", "img_url"]) {
        if (body[key] !== undefined) updates[key] = body[key];
      }
      if (body.price !== undefined) updates.price = Number(body.price);
      if (body.stock !== undefined) updates.stock = Number(body.stock);

      const { data, error } = await admin.from("products").update(updates).eq("id", productId).select("*").single();
      if (error) return fail(error.message, 400);
      return ok(data, "Product updated");
    }

    if (req.method === "DELETE" && productId && !action) {
      const { data: existing } = await admin.from("products").select("id").eq("id", productId).eq("seller_id", userId).maybeSingle();
      if (!existing) return fail("Product not found", 404);
      const { error } = await admin.from("products").delete().eq("id", productId);
      if (error) return fail(error.message, 400);
      return ok({ product_id: productId }, "Product deleted");
    }

    return fail("Method Not Allowed", 405);
  } catch (err) {
    return fail(err instanceof Error ? err.message : String(err), 500);
  }
});
