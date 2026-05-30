import { serve } from "https://deno.land/std@0.201.0/http/server.ts";
import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SUPABASE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || Deno.env.get("SUPABASE_ANON_KEY") || "";
const STORAGE_BASE = `${SUPABASE_URL}/storage/v1/object/public/hub_uploads`;

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY, {
  auth: { persistSession: false },
});

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-hub-token",
  "Access-Control-Allow-Methods": "GET,OPTIONS",
};

const respondJson = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders },
  });

const respondError = (message: string, status = 400) =>
  respondJson({ success: false, error: message }, status);

const respondOptions = () => new Response(null, { status: 204, headers: corsHeaders });

const parseId = (value: string | undefined) => {
  if (!value) return null;
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : null;
};

type SellerRow = {
  id: number;
  user_id: number;
  business_name?: string | null;
  business_logo?: string | null;
  category?: string | null;
  city?: string | null;
  province?: string | null;
  region?: string | null;
  verified?: number | null;
  shop_status?: string | null;
  approved_at?: string | null;
};

type UserRow = {
  id: number;
  email?: string | null;
  first_name?: string | null;
  last_name?: string | null;
};

function resolveImageUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const normalized = path.replace(/^\/+/, "").replace(/^uploads\//, "");
  return `${STORAGE_BASE}/${normalized}`;
}

function normalizeCategory(category: string | null | undefined): string | null {
  if (!category) return null;
  const cat = category.toLowerCase().trim();
  const categoryMap: Record<string, string> = {
    baking: "baking",
    coffee: "coffee",
    tea: "coffee",
    "coffee & tea": "coffee",
    snacks: "snacks",
    specialty: "specialty",
    organic: "organic",
    "meal kits": "mealkits",
    mealkits: "mealkits",
    "meal kit": "mealkits",
    produce: "organic",
    beverages: "coffee",
    bakery: "baking",
    "prepared meals": "mealkits",
  };
  return categoryMap[cat] ?? cat;
}

function formatSellerProfile(seller: SellerRow, user?: UserRow | null) {
  const businessName = seller.business_name?.trim() || "Unnamed Store";
  const addressParts = [seller.city, seller.province, seller.region].filter(Boolean);
  return {
    id: seller.id,
    user_id: seller.user_id,
    business_name: businessName,
    store_name: businessName,
    store_description: `${businessName} on FOODHUB`,
    store_logo: resolveImageUrl(seller.business_logo),
    store_banner: null,
    category: seller.category,
    region: seller.region,
    province: seller.province,
    city: seller.city,
    verified: seller.verified,
    shop_status: seller.shop_status,
    approved_at: seller.approved_at,
    email: user?.email ?? null,
    first_name: user?.first_name ?? null,
    last_name: user?.last_name ?? null,
    display_name: businessName,
    full_address: addressParts.length ? addressParts.join(", ") : "No address provided",
    owner_name: `${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim() || null,
  };
}

function formatActiveShop(seller: SellerRow, user: UserRow | undefined, totalProducts: number) {
  const profile = formatSellerProfile(seller, user);
  return {
    seller_id: seller.id,
    user_id: seller.user_id,
    business_name: profile.business_name,
    store_name: profile.store_name,
    store_logo: profile.store_logo,
    store_banner: profile.store_banner,
    category: seller.category,
    region: seller.region,
    province: seller.province,
    city: seller.city,
    approved_at: seller.approved_at,
    email: profile.email,
    first_name: profile.first_name,
    last_name: profile.last_name,
    total_products: totalProducts,
    store_id: null,
    shop_type: "seller",
    display_name: profile.display_name,
    full_address: profile.full_address,
    owner_name: profile.owner_name,
  };
}

async function loadSellersByUserIds(userIds: number[]) {
  if (!userIds.length) {
    return { sellersByUserId: new Map<number, SellerRow>(), usersById: new Map<number, UserRow>() };
  }

  const { data: sellers } = await supabase
    .from("sellers")
    .select("id,user_id,business_name,business_logo,category,city,province,region,verified,shop_status,approved_at")
    .in("user_id", userIds);

  const { data: users } = await supabase
    .from("users")
    .select("id,email,first_name,last_name")
    .in("id", userIds);

  const sellersByUserId = new Map<number, SellerRow>();
  for (const seller of sellers ?? []) {
    sellersByUserId.set(Number(seller.user_id), seller as SellerRow);
  }

  const usersById = new Map<number, UserRow>();
  for (const user of users ?? []) {
    usersById.set(Number(user.id), user as UserRow);
  }

  return { sellersByUserId, usersById };
}

async function loadProductImages(productIds: number[]) {
  const imagesByProduct = new Map<number, string[]>();
  if (!productIds.length) return imagesByProduct;

  const { data } = await supabase
    .from("product_images")
    .select("product_id,image_url,display_order")
    .in("product_id", productIds)
    .order("display_order", { ascending: true });

  for (const row of data ?? []) {
    const productId = Number(row.product_id);
    const resolved = resolveImageUrl(row.image_url);
    if (!resolved) continue;
    const list = imagesByProduct.get(productId) ?? [];
    list.push(resolved);
    imagesByProduct.set(productId, list);
  }

  return imagesByProduct;
}

async function loadReviewStats(productIds: number[]) {
  const stats = new Map<number, { average_rating: number; review_count: number }>();
  if (!productIds.length) return stats;

  const { data } = await supabase
    .from("reviews")
    .select("product_id,rating")
    .in("product_id", productIds);

  const buckets = new Map<number, number[]>();
  for (const row of data ?? []) {
    const productId = Number(row.product_id);
    const ratings = buckets.get(productId) ?? [];
    ratings.push(Number(row.rating) || 0);
    buckets.set(productId, ratings);
  }

  for (const [productId, ratings] of buckets.entries()) {
    const reviewCount = ratings.length;
    const average = reviewCount
      ? ratings.reduce((sum, rating) => sum + rating, 0) / reviewCount
      : 0;
    stats.set(productId, {
      average_rating: Math.round(average * 10) / 10,
      review_count: reviewCount,
    });
  }

  return stats;
}

async function enrichProducts(rawProducts: Record<string, unknown>[]) {
  if (!rawProducts.length) return [];

  const userIds = [...new Set(rawProducts.map((p) => Number(p.seller_id)).filter((id) => id > 0))];
  const productIds = rawProducts.map((p) => Number(p.id)).filter((id) => id > 0);

  const [{ sellersByUserId, usersById }, imagesByProduct, reviewStats] = await Promise.all([
    loadSellersByUserIds(userIds),
    loadProductImages(productIds),
    loadReviewStats(productIds),
  ]);

  return rawProducts
    .map((product) => {
      const sellerUserId = Number(product.seller_id);
      const seller = sellersByUserId.get(sellerUserId);
      const user = usersById.get(sellerUserId);
      const productId = Number(product.id);
      const imageUrls = imagesByProduct.get(productId) ?? [];
      const primaryImage = resolveImageUrl(String(product.img_url ?? ""));
      const allImages = imageUrls.length ? imageUrls : (primaryImage ? [primaryImage] : []);
      const review = reviewStats.get(productId) ?? { average_rating: 0, review_count: 0 };
      const businessName = seller?.business_name?.trim() || "Unknown Seller";

      return {
        ...product,
        img_url: allImages[0] ?? primaryImage,
        image_urls: allImages,
        seller_business_name: businessName,
        seller_store_name: businessName,
        seller_first_name: user?.first_name ?? null,
        seller_last_name: user?.last_name ?? null,
        shop_status: seller?.shop_status ?? null,
        average_rating: review.average_rating,
        review_count: review.review_count,
        category_normalized: normalizeCategory(String(product.category ?? "")),
      };
    })
    .filter((product) => {
      const seller = sellersByUserId.get(Number(product.seller_id));
      return seller?.verified === 1 && ["active", "warning", "suspended"].includes(String(seller?.shop_status ?? ""));
    });
}

async function fetchProductsQuery(options: {
  q?: string;
  category?: string | null;
  sellerUserId?: number | null;
  productId?: number | null;
  limit?: number;
}) {
  let query = supabase
    .from("products")
    .select("id,title,description,price,stock,seller_id,category,img_url,created_at");

  if (options.productId) query = query.eq("id", options.productId);
  if (options.sellerUserId) query = query.eq("seller_id", options.sellerUserId);
  if (options.category) query = query.eq("category", options.category);
  if (options.q) query = query.ilike("title", `%${options.q}%`);
  query = query.gt("stock", 0);

  const { data, error } = await query
    .order("created_at", { ascending: false })
    .limit(options.limit ?? 50);

  if (error) throw new Error(error.message);
  return enrichProducts((data ?? []) as Record<string, unknown>[]);
}

async function fetchActiveShops() {
  const { data: sellers, error } = await supabase
    .from("sellers")
    .select("id,user_id,business_name,business_logo,category,city,province,region,verified,shop_status,approved_at")
    .eq("verified", 1)
    .in("shop_status", ["active", "warning", "suspended"])
    .order("approved_at", { ascending: false })
    .limit(50);

  if (error) throw new Error(error.message);
  if (!sellers?.length) return [];

  const userIds = sellers.map((s) => Number(s.user_id));
  const { data: users } = await supabase
    .from("users")
    .select("id,email,first_name,last_name")
    .in("id", userIds);

  const usersById = new Map<number, UserRow>();
  for (const user of users ?? []) usersById.set(Number(user.id), user as UserRow);

  const { data: products } = await supabase
    .from("products")
    .select("seller_id")
    .in("seller_id", userIds)
    .gt("stock", 0);

  const counts = new Map<number, number>();
  for (const row of products ?? []) {
    const sellerUserId = Number(row.seller_id);
    counts.set(sellerUserId, (counts.get(sellerUserId) ?? 0) + 1);
  }

  return sellers.map((seller) =>
    formatActiveShop(
      seller as SellerRow,
      usersById.get(Number(seller.user_id)),
      counts.get(Number(seller.user_id)) ?? 0,
    )
  );
}

serve(async (req: Request) => {
  try {
    const url = new URL(req.url);
    const pathParts = url.pathname.split("/").filter(Boolean);
    const segments = pathParts.filter((part) => part !== "product_api" && part !== "api");
    const [resource, maybeId, maybeAction] = segments;

    if (req.method === "OPTIONS") return respondOptions();

    if (!resource) {
      return respondJson({
        success: true,
        message: "Supabase product API is online.",
        endpoints: [
          "GET /products",
          "GET /products/suggestions?q=term",
          "GET /products/search?q=term",
          "GET /products/best-sellers?limit=12",
          "GET /products/:id",
          "GET /products/:id/variations",
          "GET /sellers/active",
          "GET /sellers/:id",
          "GET /sellers/:id/products",
        ],
      });
    }

    if (resource === "products") {
      if (req.method !== "GET") return respondError("Method Not Allowed", 405);

      const q = url.searchParams.get("q") || url.searchParams.get("search") || "";
      const category = url.searchParams.get("category");
      const sellerId = parseId(url.searchParams.get("seller_id") || undefined);

      if (maybeId === "suggestions") {
        if (!q) return respondError("Missing search query `q`", 400);
        const products = await fetchProductsQuery({ q, limit: 12 });
        return respondJson({
          success: true,
          data: products.map((p) => ({ id: p.id, title: p.title, img_url: p.img_url })),
        });
      }

      if (maybeId === "search") {
        const products = await fetchProductsQuery({ q, limit: 50 });
        return respondJson({ success: true, data: products });
      }

      if (maybeId === "best-sellers") {
        const limit = Number(url.searchParams.get("limit") || "12");
        const { data: orderRows, error: orderError } = await supabase
          .from("order_items")
          .select("product_id,quantity");
        if (orderError) return respondError(orderError.message, 500);

        const counts = (orderRows ?? []).reduce((acc, row) => {
          const productId = Number(row.product_id);
          const quantity = Number(row.quantity || 0);
          if (!Number.isInteger(productId) || productId <= 0) return acc;
          acc[productId] = (acc[productId] || 0) + quantity;
          return acc;
        }, {} as Record<number, number>);

        const sortedIds = Object.entries(counts)
          .sort(([, a], [, b]) => b - a)
          .slice(0, limit)
          .map(([id]) => Number(id));

        if (!sortedIds.length) {
          const fallback = await fetchProductsQuery({ limit });
          return respondJson({ success: true, data: { products: fallback.slice(0, limit) } });
        }

        const { data: rawProducts, error: productsError } = await supabase
          .from("products")
          .select("id,title,description,price,stock,seller_id,category,img_url,created_at")
          .in("id", sortedIds)
          .gt("stock", 0);

        if (productsError) return respondError(productsError.message, 500);

        const productMap = (rawProducts ?? []).reduce((map, item) => {
          map[Number(item.id)] = item;
          return map;
        }, {} as Record<number, Record<string, unknown>>);

        const ordered = sortedIds.map((id) => productMap[id]).filter(Boolean);
        const products = await enrichProducts(ordered);
        const filtered = category
          ? products.filter((p) => String(p.category ?? "").toLowerCase() === category.toLowerCase())
          : products;

        return respondJson({ success: true, data: { products: filtered } });
      }

      const productId = parseId(maybeId);
      if (productId) {
        if (maybeAction === "variations") {
          const { data, error } = await supabase
            .from("product_variation_options")
            .select("id,variation_type,variation_value,price_adjustment,stock,sku,is_available")
            .eq("product_id", productId)
            .eq("is_available", true)
            .order("variation_type", { ascending: true })
            .order("id", { ascending: true });

          if (error) return respondJson({ success: true, data: [] });
          return respondJson({ success: true, data: data ?? [] });
        }

        const products = await fetchProductsQuery({ productId, limit: 1 });
        if (!products.length) return respondError("Product not found", 404);
        return respondJson({ success: true, data: products[0] });
      }

      const products = await fetchProductsQuery({
        q: q || undefined,
        category,
        sellerUserId: sellerId,
      });
      return respondJson({ success: true, data: products });
    }

    if (resource === "sellers") {
      if (req.method !== "GET") return respondError("Method Not Allowed", 405);

      if (maybeId === "active" || (!maybeId && url.searchParams.get("active") === "1")) {
        const shops = await fetchActiveShops();
        return respondJson({ success: true, data: shops, message: `${shops.length} active sellers found` });
      }

      const sellerId = parseId(maybeId);
      if (sellerId && maybeAction === "products") {
        const { data: seller, error: sellerError } = await supabase
          .from("sellers")
          .select("id,user_id,business_name,business_logo,category,city,province,region,verified,shop_status,approved_at")
          .eq("id", sellerId)
          .maybeSingle();

        if (sellerError) return respondError(sellerError.message, 500);
        if (!seller) return respondError("Seller not found", 404);

        const products = await fetchProductsQuery({ sellerUserId: Number(seller.user_id) });
        return respondJson({ success: true, data: products, message: `${products.length} products found` });
      }

      if (sellerId) {
        const { data: seller, error: sellerError } = await supabase
          .from("sellers")
          .select("id,user_id,business_name,business_logo,category,city,province,region,verified,shop_status,approved_at")
          .eq("id", sellerId)
          .maybeSingle();

        if (sellerError) return respondError(sellerError.message, 500);
        if (!seller) return respondError("Seller not found", 404);

        const { data: user } = await supabase
          .from("users")
          .select("id,email,first_name,last_name")
          .eq("id", seller.user_id)
          .maybeSingle();

        return respondJson({
          success: true,
          data: formatSellerProfile(seller as SellerRow, user as UserRow | null),
          message: "Seller profile fetched",
        });
      }

      const shops = await fetchActiveShops();
      return respondJson({ success: true, data: shops });
    }

    return respondError(`Unsupported endpoint: ${resource}`, 404);
  } catch (err) {
    return respondError(String(err), 500);
  }
});
