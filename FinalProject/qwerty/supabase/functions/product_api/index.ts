import { serve } from "https://deno.land/std@0.201.0/http/server.ts";
import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm';

const SUPABASE_URL = Deno.env.get('SUPABASE_URL');
const SUPABASE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || Deno.env.get('SUPABASE_ANON_KEY');

if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.warn('SUPABASE_URL or SUPABASE_KEY not set in function environment');
}

const supabase = createClient(SUPABASE_URL ?? '', SUPABASE_KEY ?? '', {
  auth: { persistSession: false },
});

const respondJson = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

const respondError = (message: string, status = 400) =>
  respondJson({ success: false, error: message }, status);

const parseId = (value: string | undefined) => {
  if (!value) return null;
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : null;
};

serve(async (req: Request) => {
  try {
    const url = new URL(req.url);
    const pathParts = url.pathname.split('/').filter(Boolean);
    const segments = pathParts.filter((part) => part !== 'product_api' && part !== 'api');
    const [resource, maybeId, maybeAction] = segments;

    if (req.method === 'OPTIONS') {
      return respondJson({ success: true });
    }

    if (!resource) {
      return respondJson({
        success: true,
        message: 'Supabase product API is online.',
        endpoints: [
          'GET /products',
          'GET /products/suggestions?q=term',
          'GET /products/search?q=term',
          'GET /products/best-sellers?limit=12',
          'GET /products/:id',
          'GET /sellers',
        ],
      });
    }

    if (resource === 'products') {
      if (req.method !== 'GET') {
        return respondError('Method Not Allowed', 405);
      }

      const q = url.searchParams.get('q') || url.searchParams.get('search') || '';
      const category = url.searchParams.get('category');
      const sellerId = parseId(url.searchParams.get('seller_id') || undefined);

      if (maybeId === 'suggestions') {
        if (!q) return respondError('Missing search query `q`', 400);
        const { data, error } = await supabase
          .from('products')
          .select('id,title,img_url')
          .ilike('title', `%${q}%`)
          .order('created_at', { ascending: false })
          .limit(12);

        if (error) return respondError(error.message, 500);
        return respondJson({ success: true, data });
      }

      if (maybeId === 'search') {
        const { data, error } = await supabase
          .from('products')
          .select('id,title,description,price,stock,seller_id,category,img_url,created_at')
          .ilike('title', `%${q}%`)
          .order('created_at', { ascending: false })
          .limit(50);
        if (error) return respondError(error.message, 500);
        return respondJson({ success: true, data });
      }

      if (maybeId === 'best-sellers') {
        const limit = Number(url.searchParams.get('limit') || '12');
        const category = url.searchParams.get('category');

        const { data: orderRows, error: orderError } = await supabase
          .from('order_items')
          .select('product_id,quantity');
        if (orderError) return respondError(orderError.message, 500);

        const counts = (orderRows || []).reduce((acc, row) => {
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
          return respondJson({ success: true, data: { products: [] } });
        }

        let query = supabase
          .from('products')
          .select('id,title,description,price,stock,seller_id,category,img_url,created_at')
          .in('id', sortedIds);
        if (category) {
          query = query.eq('category', category);
        }

        const { data: products, error: productsError } = await query;
        if (productsError) return respondError(productsError.message, 500);

        const productMap = (products || []).reduce((map, item) => {
          map[Number(item.id)] = item;
          return map;
        }, {} as Record<number, unknown>);

        const sortedProducts = sortedIds.map((id) => productMap[id]).filter(Boolean);
        return respondJson({ success: true, data: { products: sortedProducts } });
      }

      const productId = parseId(maybeId);
      if (productId) {
        if (maybeAction === 'variations') {
          const { data, error } = await supabase
            .from('product_variation_options')
            .select('id,variation_type,variation_value,price_adjustment,stock,sku,is_available')
            .eq('product_id', productId)
            .eq('is_available', true)
            .order('variation_type', { ascending: true })
            .order('id', { ascending: true });

          if (error) return respondJson({ success: true, data: [] });
          return respondJson({ success: true, data: data || [] });
        }

        const { data, error } = await supabase
          .from('products')
          .select('id,title,description,price,stock,seller_id,category,img_url,created_at')
          .eq('id', productId)
          .maybeSingle();

        if (error) return respondError(error.message, 500);
        if (!data) return respondError('Product not found', 404);
        return respondJson({ success: true, data });
      }

      let query = supabase
        .from('products')
        .select('id,title,description,price,stock,seller_id,category,img_url,created_at');

      if (q) {
        query = query.ilike('title', `%${q}%`);
      }
      if (category) {
        query = query.eq('category', category);
      }
      if (sellerId) {
        query = query.eq('seller_id', sellerId);
      }

      const { data, error } = await query.order('created_at', { ascending: false }).limit(50);
      if (error) return respondError(error.message, 500);
      return respondJson({ success: true, data });
    }

    if (resource === 'sellers') {
      if (req.method !== 'GET') {
        return respondError('Method Not Allowed', 405);
      }

      const { data, error } = await supabase
        .from('sellers')
        .select('id,user_id,business_name,category,city,province,region,verified,business_logo')
        .order('business_name', { ascending: true })
        .limit(50);

      if (error) return respondError(error.message, 500);
      return respondJson({ success: true, data });
    }

    return respondError(`Unsupported endpoint: ${resource}`, 404);
  } catch (err) {
    return respondError(String(err), 500);
  }
});
