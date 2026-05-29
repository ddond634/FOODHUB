import { serve } from "https://deno.land/std@0.201.0/http/server.ts";
import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm';

const SUPABASE_URL = Deno.env.get('SUPABASE_URL');
const SUPABASE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');

const supabase = createClient(SUPABASE_URL ?? '', SUPABASE_KEY ?? '');

const respondJson = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

const mapOrderPayload = (payload: any) => ({
  customer_name: payload.customer?.name || payload.customer_name || '',
  customer_phone: payload.customer?.phone || payload.customer_phone || '',
  customer_address: payload.customer?.address || payload.customer_address || '',
  subtotal: payload.subtotal != null ? Number(payload.subtotal) : 0,
  delivery_fee: payload.delivery != null ? Number(payload.delivery) : Number(payload.delivery_fee || 0),
  total: payload.total != null ? Number(payload.total) : 0,
  payment: payload.payment || 'Cash on Delivery',
  status: payload.status || 'placed',
});

const buildOrderItems = (orderId: number, items: any[]) =>
  (items || []).map((item) => ({
    order_id: orderId,
    product_id: item.product_id || item.productId || null,
    variation_id: item.variation_id || item.variationId || null,
    variation_details: item.variation_details || item.variationDetails || null,
    quantity: item.quantity != null ? Number(item.quantity) : 1,
    price: item.price != null ? Number(item.price) : 0,
  }));

serve(async (req: Request) => {
  try {
    if (req.method !== 'POST') {
      return respondJson({ success: false, error: 'Method Not Allowed' }, 405);
    }

    const payload = await req.json();
    const orderPayload = mapOrderPayload(payload);

    const { data: orderData, error: orderError } = await supabase
      .from('orders')
      .insert([orderPayload])
      .select('id')
      .single();

    if (orderError || !orderData) {
      return respondJson({ success: false, error: orderError?.message || 'Failed to create order' }, 400);
    }

    const items = buildOrderItems(orderData.id, payload.items || []);
    if (items.length > 0) {
      const { error: itemError } = await supabase.from('order_items').insert(items);
      if (itemError) {
        return respondJson({ success: false, error: itemError.message }, 400);
      }
    }

    return respondJson({ success: true, order_id: orderData.id }, 201);
  } catch (err) {
    return respondJson({ success: false, error: String(err) }, 500);
  }
});
