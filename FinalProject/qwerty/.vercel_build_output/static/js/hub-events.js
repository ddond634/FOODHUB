/**
 * Subscribe to Hub data changes broadcast by webhook_handler (via Supabase Realtime).
 * Replaces setInterval polling on shop and similar pages.
 */
(function () {
  'use strict';

  const SUPABASE_URL = 'https://sfeccfbdmbwoblixyoti.supabase.co';
  const CHANNEL_NAME = 'hub-updates';
  let client = null;
  let channel = null;
  let debounceTimer = null;

  function debounce(fn, ms) {
    return function (...args) {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve();
        return;
      }
      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Failed to load ${src}`));
      document.head.appendChild(script);
    });
  }

  async function ensureClient() {
    if (client) return client;
    if (!window.SUPABASE_ANON) return null;

    await loadScript('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js');
    if (!window.supabase || !window.supabase.createClient) return null;

    client = window.supabase.createClient(SUPABASE_URL, window.SUPABASE_ANON, {
      realtime: { params: { eventsPerSecond: 2 } },
    });
    return client;
  }

  window.hubLiveUpdates = {
    _handlers: { products: [], sellers: [], orders: [] },

    onProductsChanged(fn) {
      if (typeof fn === 'function') this._handlers.products.push(fn);
    },

    onShopsChanged(fn) {
      if (typeof fn === 'function') this._handlers.sellers.push(fn);
    },

    onOrdersChanged(fn) {
      if (typeof fn === 'function') this._handlers.orders.push(fn);
    },

    async start() {
      const supa = await ensureClient();
      if (!supa) {
        console.warn('Hub live updates unavailable — SUPABASE_ANON missing');
        return false;
      }

      if (channel) return true;

      const fireProducts = debounce(() => {
        this._handlers.products.forEach((fn) => {
          try { fn(); } catch (e) { console.warn('products handler error', e); }
        });
      }, 800);

      const fireSellers = debounce(() => {
        this._handlers.sellers.forEach((fn) => {
          try { fn(); } catch (e) { console.warn('sellers handler error', e); }
        });
      }, 800);

      const fireOrders = debounce(() => {
        this._handlers.orders.forEach((fn) => {
          try { fn(); } catch (e) { console.warn('orders handler error', e); }
        });
      }, 800);

      channel = supa.channel(CHANNEL_NAME);
      channel
        .on('broadcast', { event: 'products_changed' }, fireProducts)
        .on('broadcast', { event: 'sellers_changed' }, fireSellers)
        .on('broadcast', { event: 'orders_changed' }, fireOrders)
        .subscribe((status) => {
          if (status === 'SUBSCRIBED') {
            console.log('Hub live updates connected');
          }
        });

      return true;
    },

    stop() {
      if (client && channel) {
        client.removeChannel(channel);
        channel = null;
      }
    },
  };
})();
