import { serve } from "https://deno.land/std@0.201.0/http/server.ts";
import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm";

const SUPABASE_URL = Deno.env.get('SUPABASE_URL') ?? '';
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '';
const admin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
  auth: { persistSession: false },
});

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { 'Content-Type': 'application/json' },
});

const success = (body: unknown, status = 200) => json({ success: true, ...body }, status);
const failure = (error: string, status = 400) => json({ success: false, error }, status);

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-hub-token',
  'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
};

function withCors(res: Response) {
  const headers = new Headers(res.headers);
  Object.entries(corsHeaders).forEach(([key, value]) => headers.set(key, value));
  return new Response(res.body, { status: res.status, headers });
}

async function verifyHubToken(token: string): Promise<{ user_id: number; email?: string; role?: string } | null> {
  const secret = Deno.env.get('JWT_SECRET');
  if (!secret || !token) return null;

  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(secret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['verify'],
    );

    const data = encoder.encode(`${parts[0]}.${parts[1]}`);
    const signature = Uint8Array.from(
      atob(parts[2].replace(/-/g, '+').replace(/_/g, '/')),
      (c) => c.charCodeAt(0),
    );
    const valid = await crypto.subtle.verify('HMAC', key, signature, data);
    if (!valid) return null;

    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    if (payload.exp && Date.now() / 1000 > Number(payload.exp)) return null;

    const userId = Number(payload.user_id);
    if (!Number.isInteger(userId) || userId <= 0) return null;
    return {
      user_id: userId,
      email: typeof payload.email === 'string' ? payload.email : undefined,
      role: typeof payload.role === 'string' ? payload.role : 'customer',
    };
  } catch {
    return null;
  }
}

async function ensureHubUser(hubUser: { user_id: number; email?: string; role?: string }): Promise<number | null> {
  const { data: userById } = await admin
    .from('users')
    .select('id')
    .eq('id', hubUser.user_id)
    .maybeSingle();
  if (userById?.id) return userById.id;

  if (hubUser.email) {
    const { data: userByEmail } = await admin
      .from('users')
      .select('id')
      .eq('email', hubUser.email)
      .maybeSingle();
    if (userByEmail?.id) return userByEmail.id;
  }

  if (!hubUser.email) return null;

  const { data: created, error } = await admin
    .from('users')
    .upsert([{
      id: hubUser.user_id,
      email: hubUser.email,
      role: hubUser.role || 'customer',
      password_hash: 'flask-managed',
      is_verified: 1,
      created_at: new Date().toISOString(),
    }], { onConflict: 'id' })
    .select('id')
    .maybeSingle();

  if (error) {
    console.error('Failed to provision Hub user in Supabase:', error.message);
    return null;
  }

  return created?.id ?? hubUser.user_id;
}

async function getUserIdFromRequest(req: Request): Promise<number | null> {
  const hubToken = req.headers.get('X-Hub-Token') || '';
  if (hubToken) {
    const hubUser = await verifyHubToken(hubToken);
    if (hubUser) {
      return await ensureHubUser(hubUser);
    }
  }

  const authHeader = req.headers.get('Authorization') || '';
  const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : '';
  if (!token || token === Deno.env.get('SUPABASE_ANON_KEY')) return null;

  const { data, error } = await admin.auth.getUser(token);
  if (error || !data?.user?.email) return null;

  const { data: userRow } = await admin
    .from('users')
    .select('id')
    .eq('email', data.user.email)
    .maybeSingle();

  return userRow?.id ?? null;
}

async function getProduct(productId: number) {
  const { data, error } = await admin
    .from('products')
    .select('id,title,price,img_url,stock')
    .eq('id', productId)
    .maybeSingle();
  if (error) throw new Error(error.message);
  return data;
}

async function getVariation(variationId: number) {
  const { data, error } = await admin
    .from('product_variation_options')
    .select('id,variation_value,price_adjustment,stock,is_available')
    .eq('id', variationId)
    .maybeSingle();
  if (error) return null;
  return data;
}

async function getCartItems(userId: number) {
  const { data: rows, error } = await admin
    .from('cart_items')
    .select('id,product_id,variation_id,quantity,created_at,updated_at')
    .eq('user_id', userId)
    .order('created_at', { ascending: false });

  if (error) throw new Error(error.message);

  const items = [] as Array<Record<string, unknown>>;
  for (const row of rows || []) {
    const product = await getProduct(Number(row.product_id));
    const variation = row.variation_id ? await getVariation(Number(row.variation_id)) : null;
    const quantity = Number(row.quantity || 1);
    const unitPrice = Number(product?.price || 0) + Number(variation?.price_adjustment || 0);
    items.push({
      cart_id: row.id,
      product_id: row.product_id,
      variation_id: row.variation_id,
      quantity,
      title: product?.title || '',
      img_url: product?.img_url || '',
      variation: variation?.variation_value || null,
      unit_price: unitPrice,
      total_price: Number((unitPrice * quantity).toFixed(2)),
      stock: product?.stock ?? null,
    });
  }

  return items;
}

async function upsertCartItem(userId: number, body: Record<string, unknown>) {
  const productId = Number(body.product_id || 0);
  const quantity = Math.max(1, Number(body.quantity || 1));
  const variationId = body.variation_id === null || body.variation_id === undefined || body.variation_id === '' ? null : Number(body.variation_id);
  if (!productId) return failure('Product not found', 404);

  const product = await getProduct(productId);
  if (!product) return failure('Product not found', 404);

  let variation = null;
  if (variationId) {
    variation = await getVariation(variationId);
    if (!variation) return failure('Variation not found', 404);
  }

  const { data: existing, error: existingError } = await admin
    .from('cart_items')
    .select('id,quantity')
    .eq('user_id', userId)
    .eq('product_id', productId)
    .match(variationId === null ? {} : { variation_id: variationId })
    .maybeSingle();

  if (existingError) return failure(existingError.message, 500);

  if (existing) {
    const nextQty = Number(existing.quantity || 1) + quantity;
    const { error } = await admin
      .from('cart_items')
      .update({ quantity: nextQty, updated_at: new Date().toISOString() })
      .eq('id', existing.id);
    if (error) return failure(error.message, 400);
  } else {
    const { error } = await admin
      .from('cart_items')
      .insert([{ user_id: userId, product_id: productId, variation_id: variationId, quantity, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }]);
    if (error) return failure(error.message, 400);
  }

  return success({ message: 'Added to cart' }, 200);
}

async function updateCartItem(userId: number, cartItemId: number, quantity: number) {
  const { data: existing, error } = await admin
    .from('cart_items')
    .select('id,user_id')
    .eq('id', cartItemId)
    .maybeSingle();
  if (error) return failure(error.message, 500);
  if (!existing) return failure('Cart item not found', 404);
  if (Number(existing.user_id) !== userId) return failure('Unauthorized', 403);

  const { error: updateError } = await admin
    .from('cart_items')
    .update({ quantity: Math.max(1, quantity), updated_at: new Date().toISOString() })
    .eq('id', cartItemId);
  if (updateError) return failure(updateError.message, 400);
  return success({ message: 'Item updated' }, 200);
}

async function deleteCartItem(userId: number, cartItemId: number) {
  const { data: existing, error } = await admin
    .from('cart_items')
    .select('id,user_id')
    .eq('id', cartItemId)
    .maybeSingle();
  if (error) return failure(error.message, 500);
  if (!existing) return failure('Cart item not found', 404);
  if (Number(existing.user_id) !== userId) return failure('Unauthorized', 403);

  const { error: deleteError } = await admin.from('cart_items').delete().eq('id', cartItemId);
  if (deleteError) return failure(deleteError.message, 400);
  return success({ message: 'Item removed from cart' }, 200);
}

async function getWishlist(userId: number) {
  const { data: rows, error } = await admin
    .from('wishlist')
    .select('id,product_id,quantity,price_total,created_at')
    .eq('user_id', userId)
    .order('created_at', { ascending: false });
  if (error) throw new Error(error.message);

  const items = [] as Array<Record<string, unknown>>;
  for (const row of rows || []) {
    const product = await getProduct(Number(row.product_id));
    const quantity = Number(row.quantity || 1);
    const priceTotal = Number(row.price_total || Number(product?.price || 0) * quantity);
    items.push({
      wishlist_id: row.id,
      product_id: row.product_id,
      name: product?.title || '',
      image_url: product?.img_url || '',
      quantity,
      price: String(product?.price ?? '0.00'),
      price_total: String(priceTotal.toFixed(2)),
    });
  }
  return items;
}

async function upsertWishlistItem(userId: number, productId: number, quantity: number) {
  const product = await getProduct(productId);
  if (!product) return failure('Product not found', 404);
  const total = Number(product.price || 0) * quantity;

  const { data: existing, error } = await admin
    .from('wishlist')
    .select('id')
    .eq('user_id', userId)
    .eq('product_id', productId)
    .maybeSingle();
  if (error) return failure(error.message, 500);

  if (existing) {
    const { error: updateError } = await admin
      .from('wishlist')
      .update({ quantity, price_total: total })
      .eq('id', existing.id);
    if (updateError) return failure(updateError.message, 400);
  } else {
    const { error: insertError } = await admin
      .from('wishlist')
      .insert([{ user_id: userId, product_id: productId, quantity, price_total: total, created_at: new Date().toISOString() }]);
    if (insertError) return failure(insertError.message, 400);
  }
  return success({ message: 'Product added to wishlist' }, 200);
}

async function deleteWishlistByProduct(userId: number, productId: number) {
  const { error } = await admin
    .from('wishlist')
    .delete()
    .eq('user_id', userId)
    .eq('product_id', productId);
  if (error) return failure(error.message, 400);
  return success({ message: 'Product removed from wishlist' }, 200);
}

async function deleteWishlistById(userId: number, wishlistId: number) {
  const { data: existing, error } = await admin
    .from('wishlist')
    .select('id,user_id')
    .eq('id', wishlistId)
    .maybeSingle();
  if (error) return failure(error.message, 500);
  if (!existing) return failure('Wishlist item not found', 404);
  if (Number(existing.user_id) !== userId) return failure('Unauthorized', 403);

  const { error: deleteError } = await admin.from('wishlist').delete().eq('id', wishlistId);
  if (deleteError) return failure(deleteError.message, 400);
  return success({ message: 'Product removed from wishlist' }, 200);
}

serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return withCors(json({ success: true }));
  }

  try {
    const userId = await getUserIdFromRequest(req);
    if (!userId) {
      return withCors(failure('Unauthorized', 401));
    }

    const url = new URL(req.url);
    const path = url.pathname.split('/').filter(Boolean);
    const segments = path.filter((part) => part !== 'commerce_api' && part !== 'api');
    const [resource, identifier, action] = segments;

    if (resource === 'cart') {
      if (req.method === 'GET') {
        const items = await getCartItems(userId);
        return withCors(success({ data: { items } }, 200));
      }
      if (req.method === 'POST') {
        const body = await req.json().catch(() => ({}));
        return withCors(await upsertCartItem(userId, body));
      }
      if (req.method === 'PUT' && identifier) {
        const body = await req.json().catch(() => ({}));
        const quantity = Math.max(1, Number(body.quantity || 1));
        return withCors(await updateCartItem(userId, Number(identifier), quantity));
      }
      if (req.method === 'DELETE' && identifier) {
        return withCors(await deleteCartItem(userId, Number(identifier)));
      }
      return withCors(failure('Method Not Allowed', 405));
    }

    if (resource === 'wishlist') {
      if (req.method === 'GET') {
        const items = await getWishlist(userId);
        return withCors(success({ items }, 200));
      }
      if (req.method === 'POST' && identifier) {
        const body = await req.json().catch(() => ({}));
        const quantity = Math.max(1, Number(body.quantity || 1));
        return withCors(await upsertWishlistItem(userId, Number(identifier), quantity));
      }
      if (req.method === 'DELETE' && identifier === 'remove' && action) {
        return withCors(await deleteWishlistById(userId, Number(action)));
      }
      if (req.method === 'DELETE' && identifier) {
        return withCors(await deleteWishlistByProduct(userId, Number(identifier)));
      }
      return withCors(failure('Method Not Allowed', 405));
    }

    return withCors(failure(`Unsupported endpoint: ${resource || 'root'}`, 404));
  } catch (error) {
    return withCors(failure(error instanceof Error ? error.message : String(error), 500));
  }
});
