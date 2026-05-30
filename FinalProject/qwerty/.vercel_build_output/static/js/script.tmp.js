// Cart utilities - clean rebuild
(function(){
  // ============ IMMEDIATE CLEANUP - RUNS FIRST ============
  // Clear ALL cart/wishlist data if not logged in (runs synchronously before anything else)
  (function immediateCleanup() {
    // SKIP cleanup on login/register pages
    const currentPath = window.location.pathname.toLowerCase();
    const isAuthPage = currentPath.includes('loginregister') || 
                      currentPath.includes('login.html') || 
                      currentPath.includes('register.html');
    
    if (isAuthPage) {
      console.log('✅ Auth page - skipping cart/wishlist cleanup');
      return;
    }
    
    const token = localStorage.getItem('hub_access_token');
    if (!token) {
      console.log('🔍 No token found - clearing all cart/wishlist data');
      // Clear ALL cart and wishlist keys immediately
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && (key.includes('cart') || key.includes('wishlist'))) {
          keysToRemove.push(key);
        }
      }
      console.log('🗑️ Found keys to remove:', keysToRemove);
      keysToRemove.forEach(key => {
        localStorage.removeItem(key);
        console.log('✅ Cleared:', key);
      });
      
      // NUCLEAR OPTION: Set empty arrays to force override any cached values
      localStorage.setItem('hub_cart_v1', JSON.stringify([]));
      localStorage.setItem('hub_wishlist_v1', JSON.stringify([]));
      
      // Hide badges immediately if they exist (wait a bit for DOM)
      setTimeout(() => {
        const cartBadge = document.querySelector('#cartBtn .badge');
        const wishlistBadge = document.querySelector('#wishlistBtn .badge');
        if (cartBadge) {
          cartBadge.style.display = 'none';
          console.log('📛 Hidden cart badge (no account)');
        }
        if (wishlistBadge) {
          wishlistBadge.style.display = 'none';
          console.log('📛 Hidden wishlist badge (no account)');
        }
      }, 100);
    } else {
      console.log('✅ Token found - user is logged in');
    }
  })();
  // ============ END IMMEDIATE CLEANUP ============
  
  // Global loading overlay utilities
  (function(){
    // Create loader element if not present
    let loader = document.querySelector('.global-loader');
    if (!loader) {
      loader = document.createElement('div');
      loader.className = 'global-loader';
      loader.setAttribute('aria-hidden', 'true');
      loader.innerHTML = '<div class="spinner" role="status" aria-label="Loading"></div><div class="loader-text">Loading...</div>';
      loader.hidden = true;
      document.addEventListener('DOMContentLoaded', () => document.body.appendChild(loader));
      // If DOM already loaded, append immediately
      if (document.readyState === 'complete' || document.readyState === 'interactive') document.body.appendChild(loader);
    }

    let counter = 0;
    function showGlobalLoader(){
      try{
        counter++;
        loader.hidden = false;
        loader.setAttribute('aria-hidden','false');
      }catch(e){/* ignore */}
    }
    function hideGlobalLoader(){
      try{
        counter = Math.max(0, counter-1);
        if(counter === 0){ loader.hidden = true; loader.setAttribute('aria-hidden','true'); }
      }catch(e){/* ignore */}
    }

    // Expose globally for other scripts
    window.showGlobalLoader = showGlobalLoader;
    window.hideGlobalLoader = hideGlobalLoader;

    // Supabase Edge Function and storage configuration
    const SUPABASE_PROJECT_REF = 'sfeccfbdmbwoblixyoti';
    const SUPABASE_FUNCTIONS_BASE = `https://${SUPABASE_PROJECT_REF}.functions.supabase.co`;
    const SUPABASE_PRODUCT_API = `${SUPABASE_FUNCTIONS_BASE}/product_api`;
    const SUPABASE_COMMERCE_API = `${SUPABASE_FUNCTIONS_BASE}/commerce_api`;
    const SUPABASE_ORDER_API = `${SUPABASE_FUNCTIONS_BASE}/create_order`;
    const SUPABASE_STORAGE_BASE = `https://${SUPABASE_PROJECT_REF}.supabase.co/storage/v1/object/public/hub_uploads`;
    const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNmZWNjZmJkbWJ3b2JsaXh5b3RpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwODAwNTksImV4cCI6MjA5NTY1NjA1OX0.uM7DX7T-PQqPsMIwh-Fna1BUtVkkOhR4PiT2YqYlhIE';

    window.SUPABASE_FUNCTIONS_BASE = SUPABASE_FUNCTIONS_BASE;
    window.SUPABASE_PRODUCT_API = SUPABASE_PRODUCT_API;
    window.SUPABASE_COMMERCE_API = SUPABASE_COMMERCE_API;
    window.SUPABASE_ORDER_API = SUPABASE_ORDER_API;
    window.SUPABASE_STORAGE_BASE = SUPABASE_STORAGE_BASE;
    window.SUPABASE_ANON = SUPABASE_ANON;

    function resolveStorageUrl(path) {
      if (!path) return path;
      if (typeof path !== 'string') return path;
      if (path.startsWith('http://') || path.startsWith('https://')) return path;
      const normalized = path.replace(/^\/+/, '').replace(/^uploads\//, '');
      return `${SUPABASE_STORAGE_BASE}/${normalized}`;
    }

    window.resolveStorageUrl = resolveStorageUrl;

    // Monkey-patch fetch to automatically show loader for network requests
    if (window.fetch) {
      const origFetch = window.fetch.bind(window);

      const isSupabaseFunctionUrl = (url) => {
        try {
          return typeof url === 'string' && url.includes(`${SUPABASE_PROJECT_REF}.functions.supabase.co`);
        } catch (err) {
          return false;
        }
      };

      const rewriteLegacyApiUrl = (urlValue) => {
        try {
          const url = new URL(urlValue, window.location.origin);
          const path = url.pathname;
          if (!path.startsWith('/api/')) return urlValue;

          const legacyHost = url.hostname === 'localhost' || url.hostname === '127.0.0.1' || url.origin === window.location.origin;
          if (!legacyHost) return urlValue;

          const resourcePath = path.replace(/^\/api/, '');
          const query = url.search || '';

          if (resourcePath.startsWith('/cart') || resourcePath.startsWith('/wishlist')) {
            return `${SUPABASE_COMMERCE_API}${resourcePath}${query}`;
          }
          if (resourcePath.startsWith('/products/best-sellers')) {
            return `${SUPABASE_PRODUCT_API}/products${query}`;
          }
          if (resourcePath.startsWith('/products')) {
            return `${SUPABASE_PRODUCT_API}${resourcePath}${query}`;
          }
          if (resourcePath.startsWith('/sellers/active')) {
            return `${SUPABASE_PRODUCT_API}/sellers${query}`;
          }

          return urlValue;
        } catch (err) {
          return urlValue;
        }
      };

      const addSupabaseFunctionHeaders = (input, init) => {
        const authHeaders = {
          Authorization: `Bearer ${SUPABASE_ANON}`,
          apikey: SUPABASE_ANON,
        };

        if (input instanceof Request) {
          const headers = new Headers(input.headers || {});
          Object.entries(authHeaders).forEach(([key, value]) => {
            if (!headers.has(key)) headers.set(key, value);
          });
          return [new Request(input, { headers }), init];
        }

        init = init || {};
        init.headers = new Headers(init.headers || {});
        Object.entries(authHeaders).forEach(([key, value]) => {
          if (!init.headers.has(key)) init.headers.set(key, value);
        });
        return [input, init];
      };

      window.fetch = function(...args){
        try {
          if (args.length > 0) {
            let [input, init] = args;
            if (typeof input === 'string') {
              input = rewriteLegacyApiUrl(input);
            } else if (input instanceof Request) {
              const rewrittenUrl = rewriteLegacyApiUrl(input.url);
              if (rewrittenUrl !== input.url) {
                input = new Request(rewrittenUrl, input);
              }
            }

            if (isSupabaseFunctionUrl(input) || (input instanceof Request && isSupabaseFunctionUrl(input.url))) {
              [input, init] = addSupabaseFunctionHeaders(input, init);
            }

            args = [input, init];
          }
        } catch (err) {
          console.error('Supabase fetch wrapper failed', err);
        }
        showGlobalLoader();
        return origFetch(...args)
          .then(res => { hideGlobalLoader(); return res; })
          .catch(err => { hideGlobalLoader(); throw err; });
      };
    }
  })();
  const STORAGE_KEY='hub_cart_v1';
  const PESO='₱';
  const Q=(s)=>document.querySelector(s);
  
  // Authentication helper
  function isUserLoggedIn() {
    const token = localStorage.getItem('hub_access_token');
    return !!token;
  }
  
  function getUserId() {
    const token = localStorage.getItem('hub_access_token');
    if (!token) return null;
    try {
      const parts = token.split('.');
      const decoded = JSON.parse(atob(parts[1]));
      return decoded.user_id || null;
    } catch (e) {
      return null;
    }
  }
  
  function getUserSpecificKey(baseKey) {
    const userId = getUserId();
    return userId ? `${baseKey}_user_${userId}` : baseKey;
  }
  
  function clearUnauthenticatedData() {
    // SKIP on auth pages
    const currentPath = window.location.pathname.toLowerCase();
    const isAuthPage = currentPath.includes('loginregister') || 
                      currentPath.includes('login.html') || 
                      currentPath.includes('register.html');
    if (isAuthPage) return;
    
    // Clear any cart/wishlist data that doesn't have user association
    if (!isUserLoggedIn()) {
      console.log('🔒 User not logged in - clearing all cart/wishlist data');
      // Clear all cart and wishlist related keys
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && (key.includes('cart') || key.includes('wishlist'))) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach(key => {
        localStorage.removeItem(key);
        console.log('🗑️ Cleared:', key);
      });
      console.log('✅ Cart/wishlist cleanup complete');
    }
  }
  
  // IMMEDIATELY clear unauthenticated data on script load
  clearUnauthenticatedData();
  
  function getCart(){ 
    // Return empty cart if not logged in
    if (!isUserLoggedIn()) return [];
    
    const key = getUserSpecificKey(STORAGE_KEY);
    try{
      return JSON.parse(localStorage.getItem(key)||'[]');
    }catch(e){
      console.error(e);
      return[];
    } 
  }
  function saveCart(c){
    // Don't save if not logged in
    if (!isUserLoggedIn()) {
      console.warn('Cannot save cart: user not logged in');
      return;
    }
    
    const key = getUserSpecificKey(STORAGE_KEY);
    try {
      localStorage.setItem(key, JSON.stringify(c));
    } catch(e){ console.error(e); }
    // Emit cart updated event so any page can refresh badges/dropdowns without manual calls
    try { window.dispatchEvent(new CustomEvent('cart:updated', { detail:{ cart:c } })); } catch(e) {}
  }
  function findItem(c,t){ return c.find(i=>i.title===t); }
  function normalizePrice(txt){ if(!txt) return 0; const d=(''+txt).replace(/[^0-9.]/g,''); return Number(d)||0; }

  // Fetch cart count from backend and update badge
  async function updateCartBadge() {
    const badge = Q('#cartBtn .badge');
    const cartCount = Q('#cartCount');
    
    if (!isUserLoggedIn()) {
      // Hide badges when not logged in
      if (badge) badge.style.display = 'none';
      if (cartCount) cartCount.textContent = 0;
      return;
    }
    
    try {
      const token = localStorage.getItem('hub_access_token');
      const response = await fetch(`${window.SUPABASE_COMMERCE_API}/cart`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      
      // Backend returns { success: true, data: { items: [...] }, message: '...' }
      if (data.success && data.data && data.data.items) {
        const totalItems = data.data.items.reduce((sum, item) => sum + (item.quantity || 0), 0);
        if (badge) {
          badge.textContent = totalItems;
          // Show badge only if there are items
          badge.style.display = totalItems > 0 ? 'inline-block' : 'none';
          badge.classList.remove('pulse'); 
          void badge.offsetWidth; 
          badge.classList.add('pulse');
        }
        if (cartCount) cartCount.textContent = totalItems;
      } else {
        // No items or error - hide badge
        if (badge) badge.style.display = 'none';
      }
    } catch (error) {
      console.error('Error updating cart badge:', error);
      if (badge) badge.style.display = 'none';
    }
  }
  
  // Fetch wishlist count from backend and update badge
  async function updateWishlistBadge() {
    const badge = Q('#wishlistBtn .badge');
    
    if (!isUserLoggedIn()) {
      // Hide badge when not logged in
      if (badge) badge.style.display = 'none';
      return;
    }
    
    try {
      const token = localStorage.getItem('hub_access_token');
      const response = await fetch(`${window.SUPABASE_COMMERCE_API}/wishlist`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      
      if (data.success && data.items) {
        if (badge) {
          badge.textContent = data.items.length;
          // Show badge only if there are items
          badge.style.display = data.items.length > 0 ? 'inline-block' : 'none';
          badge.classList.remove('pulse'); 
          void badge.offsetWidth; 
          badge.classList.add('pulse');
        }
      } else {
        // No items or error - hide badge
        if (badge) badge.style.display = 'none';
      }
    } catch (error) {
      console.error('Error updating wishlist badge:', error);
      if (badge) badge.style.display = 'none';
    }
  }
  
  // Legacy updateBadges for compatibility
  function updateBadges(){
    updateCartBadge();
    updateWishlistBadge();
  }

  // Global sync functions for external use
  window.syncWishlistBadge = updateWishlistBadge;
  window.syncCartBadge = updateCartBadge;

  // Fetch cart from backend and render dropdown
  async function renderCartDropdown(){
    const dd=Q('#cartDropdown'); 
    if(!dd) return;
    
    if (!isUserLoggedIn()) {
      const itemsEl=dd.querySelector('.dropdown-items'); 
      const footerCount=dd.querySelector('.items-count'); 
      if(itemsEl) itemsEl.innerHTML='<div style="padding:18px;color:#666">Please log in to view your cart</div>'; 
      if(footerCount) footerCount.textContent='0 items in cart';
      return;
    }
    
    try {
      const token = localStorage.getItem('hub_access_token');
      const response = await fetch(`${window.SUPABASE_COMMERCE_API}/cart`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      
      const itemsEl=dd.querySelector('.dropdown-items'); 
      const footerCount=dd.querySelector('.items-count');
      if(!itemsEl) return;
      
      // Backend returns { success: true, data: { items: [...] }, message: '...' }
      const items = (data.success && data.data && data.data.items) ? data.data.items : [];
      
      if (items.length === 0) {
        itemsEl.innerHTML='<div style="padding:18px;color:#666">Your cart is empty</div>'; 
        if(footerCount) footerCount.textContent='0 items in cart';
        return;
      }
      
      const cartItems = items.slice(0, 5); // Show last 5 items
      itemsEl.innerHTML = cartItems.map(item => `
        <div class="dropdown-item">
          <img src="${resolveStorageUrl(item.img_url || '/uploads/placeholder.jpg')}" 
               alt="${item.title}" loading="lazy" 
               onerror="this.src='https://via.placeholder.com/60'">
          <div class="item-details">
            <p class="item-name">${item.title}</p>
            <p class="item-price">${PESO}${parseFloat(item.unit_price).toFixed(2)} × ${item.quantity}</p>
          </div>
        </div>
      `).join('');
      
      const totalQty = items.reduce((sum, item) => sum + item.quantity, 0);
      if(footerCount) footerCount.textContent=`${totalQty} items in cart`;
    } catch (error) {
      console.error('Error rendering cart dropdown:', error);
    }
  }
  // Fetch wishlist from backend and render dropdown
  async function renderWishlistDropdown(){
    const dd=Q('#wishlistDropdown'); 
    if(!dd) return;
    
    if (!isUserLoggedIn()) {
      const header='<div class="dropdown-header">Recently Added to Wishlist</div>';
      const items='<div class="dropdown-items"><div style="padding:18px;color:#666">Please log in to view your wishlist</div></div>';
      const footer='<div class="dropdown-footer"><p class="items-count">0 item(s) in wishlist</p><button class="view-btn">View My Wishlist</button></div>';
      dd.innerHTML=header+items+footer;
      return;
    }
    
    try {
      const token = localStorage.getItem('hub_access_token');
      const response = await fetch(`${window.SUPABASE_COMMERCE_API}/wishlist`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      
      const header='<div class="dropdown-header">Recently Added to Wishlist</div>';
      let items = '<div class="dropdown-items">';
      
      if (!data.success || !data.items || data.items.length === 0) {
        items += '<div style="padding:18px;color:#666">Your wishlist is empty</div>';
      } else {
        const recentItems = data.items.slice(0, 5);
        items += recentItems.map(item => {
          // Handle price - use price if available, otherwise use price_total, fallback to 0
          let price = 0;
          if (item.price && !isNaN(parseFloat(item.price))) {
            price = parseFloat(item.price);
          } else if (item.price_total && !isNaN(parseFloat(item.price_total))) {
            const quantity = parseInt(item.quantity) || 1;
            price = parseFloat(item.price_total) / quantity;
          }
          
          return `
          <div class="dropdown-item">
            <img src="${resolveStorageUrl(item.image_url || 'uploads/placeholder.jpg')}" 
                 alt="${item.name || 'Product'}" loading="lazy"
                 onerror="this.src='https://via.placeholder.com/60'">
            <div class="item-details">
              <p class="item-name">${item.name || 'Unknown Product'}</p>
              <p class="item-price">${PESO}${price.toFixed(2)}</p>
            </div>
          </div>
        `;
        }).join('');
      }
      items += '</div>';
      
      const footer=`<div class="dropdown-footer"><p class="items-count">${data.items ? data.items.length : 0} item(s) in wishlist</p><button class="view-btn" onclick="window.location.href='wishlist.html'">View My Wishlist</button></div>`;
      dd.innerHTML=header+items+footer;
    } catch (error) {
      console.error('Error rendering wishlist dropdown:', error);
    }
  }

  function addToCartFromButton(btn){
    // Check authentication first
    if (!isUserLoggedIn()) {
      if (window.notify) {
        window.notify.warning('Please log in to add items to your cart.');
      }
      setTimeout(() => {
        window.location.href = 'loginregister.html';
      }, 1500);
      return;
    }
    
    if(!btn) return; let title=btn.getAttribute('data-product')||''; const card=btn.closest('.product-card,.product-shop-card,.arrival-product-card,.card-back')||document.createElement('div'); if(!title){ const h=card.querySelector('h4, h3, .product-shop-title'); title=h?h.textContent.trim():'Unknown product'; }
    let priceRaw=btn.getAttribute('data-price')||''; let price=normalizePrice(priceRaw); if(!price){ const pt=card.querySelector('.price-tag,.product-price,.price,.price-current'); if(pt) price=normalizePrice(pt.textContent); }
    const imgEl=card.querySelector('img'); const img=imgEl?imgEl.src:''; const descEl=card.querySelector('.product-info p, p'); const desc=descEl?descEl.textContent.trim():''; const seller=btn.getAttribute('data-seller')||'Unknown Seller';
    // Try to get product_id from button or card data attributes
    const productId=btn.getAttribute('data-product-id')||card.getAttribute('data-product-id')||btn.getAttribute('data-id')||card.getAttribute('data-id')||null;
    // Show loader while processing add-to-cart
    const originalAria = btn.getAttribute('aria-busy');
    try { btn.setAttribute('aria-busy','true'); showGlobalLoader(); } catch(e){}
    const cart=getCart(); // perform add after a small simulated delay to show loader
    setTimeout(()=>{
      const existing=findItem(cart,title);
      if(existing){ existing.quantity=(existing.quantity||1)+1; if(productId && !existing.product_id) existing.product_id=productId; }
      else { cart.push({title,price,img,desc,quantity:1,seller,product_id:productId||null}); }
      saveCart(cart); updateBadges(); renderCartDropdown(); try{btn.classList.add('added'); setTimeout(()=>btn.classList.remove('added'),500);}catch(e){}
      showToast(`${title} added to cart`);
      try { btn.setAttribute('aria-busy', originalAria===null ? 'false' : originalAria); } catch(e){}
      hideGlobalLoader();
    }, 350);
  }

  function showToast(text,timeout=2500){ let c=document.querySelector('.toast-container'); if(!c){ c=document.createElement('div'); c.className='toast-container'; document.body.appendChild(c);} const t=document.createElement('div'); t.className='toast'; t.textContent=text; c.appendChild(t); requestAnimationFrame(()=>t.classList.add('show')); setTimeout(()=>{ t.classList.remove('show'); setTimeout(()=>t.remove(),260); }, timeout); }

  function renderCartPage(){ const cart=getCart(); const itemsEl=Q('#cartItems'); const summaryEl=Q('#cartSummary'); const emptyEl=Q('#emptyCart'); const countEl=Q('#cartCount'); if(!itemsEl||!summaryEl||!emptyEl) return; if(!cart.length){ itemsEl.style.display='none'; summaryEl.hidden=true; emptyEl.hidden=false; if(countEl) countEl.textContent=0; updateSummary(); return; }
    itemsEl.style.display='flex'; summaryEl.hidden=false; emptyEl.hidden=true; const totalItems=cart.reduce((s,i)=>s+(i.quantity||0),0); if(countEl) countEl.textContent=totalItems;
  const groups=cart.reduce((a,it,idx)=>{ const s=it.seller||'Unknown Seller'; (a[s]=a[s]||[]).push({...it,_idx:idx}); return a; },{});
  const html=Object.keys(groups).map(seller=>{ const rows=groups[seller].map(item=>{ const lineTotal=(item.price||0)*(item.quantity||0); const oldPrice=Math.round((item.price||0)*1.12); return `<div class="cart-item" data-index="${item._idx}" data-seller="${seller}"><div class="ci-col ci-check"><input type="checkbox" class="item-check" data-index="${item._idx}"></div><div class="ci-col ci-product"><img src="${item.img}" alt="${item.title}" class="cart-item-img"><div class="ci-info"><h3 class="ci-title">${item.title}</h3><p class="ci-desc">${item.desc||''}</p></div></div><div class="ci-col ci-unit"><span class="price-old">${PESO}${oldPrice}</span><span class="price-now">${PESO}${item.price}</span></div><div class="ci-col ci-qty"><div class="quantity-control" role="group" aria-label="Quantity controls"><button class="quantity-btn" data-action="decrease" data-index="${item._idx}" aria-label="Decrease quantity">-</button><span class="quantity-value" aria-live="polite">${item.quantity}</span><button class="quantity-btn" data-action="increase" data-index="${item._idx}" aria-label="Increase quantity">+</button></div></div><div class="ci-col ci-total"><span class="total-price">${PESO}${lineTotal}</span></div><div class="ci-col ci-actions"><button class="link-delete" data-action="remove" data-index="${item._idx}" aria-label="Remove item">Delete</button></div></div>`; }).join(''); return `<div class="seller-group" data-seller="${seller}"><div class="seller-header"><label><input type="checkbox" class="seller-toggle"> </label><div class="seller-name">${seller}</div></div>${rows}</div>`; }).join(''); itemsEl.innerHTML=html; updateSummary(); if(window.syncSelectionStates) window.syncSelectionStates(); }

  function updateSummary(){
    const cart=getCart();
    // Determine selected items (by checkbox) if present; otherwise fall back to all items
    const cont=Q('#cartItems');
    let selectedItems=[];
    if(cont){
      const idxs=Array.from(cont.querySelectorAll('.item-check:checked')).map(cb=>Number(cb.getAttribute('data-index')));
      if(idxs.length){ selectedItems=idxs.map(i=>cart[i]).filter(Boolean); }
    }
    if(!selectedItems.length){
      // If nothing selected, treat as zero for totals; still show All count separately
      selectedItems=[];
    }
    const subtotal=selectedItems.reduce((s,i)=>s+((i.price||0)*(i.quantity||0)),0);
    const delivery=subtotal>0 ? 50 : 0;
    const total=subtotal+delivery;
    // Old sidebar summary (kept for reference but hidden via CSS)
    const subEl=Q('#subtotal'); const delEl=Q('#deliveryFee'); const totEl=Q('#total');
    if(subEl) subEl.textContent=PESO+subtotal;
    if(delEl) delEl.textContent=PESO+delivery;
    if(totEl) totEl.textContent=PESO+total;
    // Footer summary
    const bar=Q('#cartFooterBar');
    const fTotal=Q('#footerTotal'); const fCount=Q('#footerCount');
    const fsSubtotal=Q('#fsSubtotal'); const fsDelivery=Q('#fsDelivery');
    if(fsSubtotal) fsSubtotal.textContent=PESO+subtotal;
    if(fsDelivery) fsDelivery.textContent=PESO+delivery;
    const allCount=Q('#footerAllCount'); if(allCount) allCount.textContent=cart.length;
    if(bar&&fTotal&&fCount){
      if(!cart.length){ bar.hidden=true; }
      else {
        bar.hidden=false;
        const qty=selectedItems.reduce((s,i)=>s+(i.quantity||0),0);
        fTotal.textContent=PESO+total;
        fCount.textContent=qty;
      }
    }
  }

  function updateQuantityByIndex(idx,chg){ const cart=getCart(); const item=cart[idx]; if(!item) return; item.quantity=(item.quantity||1)+chg; if(item.quantity<=0) cart.splice(idx,1); saveCart(cart); renderCartPage(); renderCartDropdown(); updateBadges(); }
  function removeFromCartByIndex(idx){ const cart=getCart(); if(idx<0||idx>=cart.length) return; cart.splice(idx,1); saveCart(cart); renderCartPage(); renderCartDropdown(); updateBadges(); }
  
  function checkout(){ 
    const cart=getCart(); 
    const cont=Q('#cartItems'); 
    if(!cont) return; // Cart not loaded - silent return, handled by cart.html
    const selectedIdxs=Array.from(cont.querySelectorAll('.item-check:checked')).map(cb=>Number(cb.getAttribute('data-index')));
    if(!selectedIdxs.length) return; // No items selected - silent return, handled by cart.html notification
    const selectedItems=selectedIdxs.map(i=>cart[i]).filter(Boolean);
    const subtotal=selectedItems.reduce((s,i)=>s+((i.price||0)*(i.quantity||0)),0);
    const delivery=subtotal>0 ? 50 : 0;
    const total=subtotal+delivery;
    const qty=selectedItems.reduce((s,i)=>s+(i.quantity||0),0);
    
    // Open checkout modal
    const modal=Q('#checkoutModal');
    if(!modal) return; // Checkout modal not found - silent return
    
    // Populate order summary
    const itemCount=Q('#checkoutItemCount');
    const checkoutSub=Q('#checkoutSubtotal');
    const checkoutDel=Q('#checkoutDelivery');
    const checkoutTot=Q('#checkoutTotal');
    if(itemCount) itemCount.textContent=qty;
    if(checkoutSub) checkoutSub.textContent=PESO+subtotal;
    if(checkoutDel) checkoutDel.textContent=PESO+delivery;
    if(checkoutTot) checkoutTot.textContent=PESO+total;
    
    modal.hidden=false;
    document.body.style.overflow='hidden';
  }

  function wireSelectionControls(){ const cont=Q('#cartItems'); if(!cont) return; const selAll=Q('#selectAll'); const footSel=Q('#footerSelectAll'); const delBtn=Q('#footerDelete'); const chkBtn=document.querySelector('.cart-footer-bar .btn-checkout'); const itemChecks=()=>Array.from(cont.querySelectorAll('.item-check')); const sellerGroups=()=>Array.from(cont.querySelectorAll('.seller-group')); const sellerToggle=g=>g.querySelector('.seller-toggle'); function syncSeller(){ sellerGroups().forEach(g=>{ const items=Array.from(g.querySelectorAll('.item-check')); const t=sellerToggle(g); if(!t) return; t.checked=items.length && items.every(i=>i.checked); }); } function syncGlobal(){ const items=itemChecks(); const all=items.length && items.every(i=>i.checked); if(selAll) selAll.checked=all; if(footSel) footSel.checked=all; } window.syncSelectionStates=()=>{ syncSeller(); syncGlobal(); updateSummary(); }; cont.addEventListener('change',e=>{ if(e.target.classList.contains('item-check')){ syncSeller(); syncGlobal(); updateSummary(); } if(e.target.classList.contains('seller-toggle')){ const g=e.target.closest('.seller-group'); const items=Array.from(g.querySelectorAll('.item-check')); items.forEach(cb=>cb.checked=e.target.checked); syncGlobal(); updateSummary(); } }); function setAll(c){ itemChecks().forEach(cb=>cb.checked=c); syncSeller(); syncGlobal(); updateSummary(); } if(selAll) selAll.addEventListener('change',e=>setAll(e.target.checked)); if(footSel) footSel.addEventListener('change',e=>setAll(e.target.checked)); if(delBtn) delBtn.addEventListener('click',()=>{ const selected=itemChecks().filter(c=>c.checked).map(c=>Number(c.getAttribute('data-index'))).sort((a,b)=>b-a); if(!selected.length) return alert('No items selected'); const cart=getCart(); selected.forEach(i=>{ if(i>=0&&i<cart.length) cart.splice(i,1); }); saveCart(cart); renderCartPage(); renderCartDropdown(); updateBadges(); }); if(chkBtn) chkBtn.addEventListener('click',checkout); }

  function initCart(){ 
    // Clear unauthenticated data on init
    clearUnauthenticatedData();
    
    updateBadges(); 
    renderCartDropdown(); 
    document.addEventListener('click',e=>{ 
    // Catch standard cart buttons and shop-specific add buttons
    const btn = e.target.closest('.btn-cart, .btn-add-circle');
    if(btn){
      e.preventDefault();
      // If it's an add button, add to cart
      if(btn.classList.contains('btn-add-circle') || btn.classList.contains('btn-cart')){
        addToCartFromButton(btn);
      }
      return; 
    }
    const q=e.target.closest('[data-action]'); if(q){ const act=q.getAttribute('data-action'); const idx=Number(q.getAttribute('data-index')); if(idx>=0){ if(act==='decrease') updateQuantityByIndex(idx,-1); if(act==='increase') updateQuantityByIndex(idx,1); if(act==='remove') removeFromCartByIndex(idx); } } }); if(Q('#cartItems')){ renderCartPage(); wireSelectionControls(); } }

  // Floating support panel (chat placeholder)
  // Support button now redirects to chat.html via onclick
  
  // Navbar behaviors copied from index: sticky on scroll + categories, wishlist, and cart dropdowns
  function initNavbarFeatures(){
    const navbar=document.getElementById('navbar');
    const categoriesToggle=document.getElementById('categoriesToggle');
    const categoriesPanel=document.getElementById('categoriesPanel');
    const wishlistBtn=document.getElementById('wishlistBtn');
    const wishlistDropdown=document.getElementById('wishlistDropdown');
    const cartBtn=document.getElementById('cartBtn');
    const cartDropdown=document.getElementById('cartDropdown');

    // Helper to close both dropdowns
    const closeDropdown = (el)=>{ if(!el) return; el.classList.remove('open'); el.hidden=true; };
    const openDropdown = (el)=>{ if(!el) return; el.hidden=false; el.classList.add('open'); };

    // Sticky navbar on scroll (full feature parity)
    if(navbar){
      // Align sticky/expanded behavior with original index.html intent (expanded on scroll >80)
      const applySticky=()=>{
        if(window.scrollY>80){
          navbar.classList.add('sticky');
          navbar.classList.add('expanded');
        } else {
          navbar.classList.remove('sticky');
          // only remove expanded if categories panel not open
          if(!categoriesPanel || categoriesPanel.hidden) navbar.classList.remove('expanded');
        }
      };
      applySticky();
      window.addEventListener('scroll', applySticky, { passive:true });
    }

    // Categories dropdown expand/collapse
    if(categoriesToggle && categoriesPanel){
      const setCatOpen=(open)=>{
        categoriesPanel.hidden=!open;
        categoriesPanel.classList.toggle('open', open);
        categoriesToggle.setAttribute('aria-expanded', open? 'true':'false');
        // Use a distinct classname to indicate categories panel open without
        // changing the navbar width (avoid the layout jump caused by .expanded)
        if(navbar) navbar.classList.toggle('categories-open', open);
      };
      categoriesToggle.addEventListener('click', (e)=>{
        e.preventDefault();
        setCatOpen(categoriesPanel.hidden);
      });
      document.addEventListener('click', (e)=>{
        if(categoriesPanel.hidden) return;
        if(e.target.closest('#categoriesPanel') || e.target.closest('#categoriesToggle')) return;
        setCatOpen(false);
      });
      document.addEventListener('keydown', (e)=>{ if(e.key==='Escape') setCatOpen(false); });
    }

    // Wishlist dropdown open/close
    // Skip wishlist dropdown on wishlist page itself
    if(wishlistBtn && wishlistDropdown && !document.body.classList.contains('wishlist-page')){
      const setWishOpen=(open)=>{ if(open){ closeDropdown(cartDropdown); if(typeof renderWishlistDropdown==='function'){ try{ renderWishlistDropdown(); }catch(_){} } openDropdown(wishlistDropdown); } else { closeDropdown(wishlistDropdown); } };
      wishlistBtn.addEventListener('click', (e)=>{
        e.preventDefault();
        const willOpen = wishlistDropdown.hidden || !wishlistDropdown.classList.contains('open');
        setWishOpen(willOpen);
      });
      document.addEventListener('click', (e)=>{
        if(!wishlistDropdown.classList.contains('open')) return;
        if(e.target.closest('#wishlistDropdown') || e.target.closest('#wishlistBtn')) return;
        setWishOpen(false);
      });
      document.addEventListener('keydown', (e)=>{ if(e.key==='Escape') setWishOpen(false); });
    }

    // Cart dropdown open/close (and populate on open)
    if(cartBtn && cartDropdown){
      const setCartOpen=(open)=>{
        if(open){
          closeDropdown(wishlistDropdown);
          if(typeof renderCartDropdown==='function'){ try{ renderCartDropdown(); }catch(_){} }
          openDropdown(cartDropdown);
        } else { closeDropdown(cartDropdown); }
      };
      cartBtn.addEventListener('click', (e)=>{
        // If the cart icon is an anchor to cart.html, only toggle when modifier isn't used
        e.preventDefault();
        const willOpen = cartDropdown.hidden || !cartDropdown.classList.contains('open');
        setCartOpen(willOpen);
      });
      document.addEventListener('click', (e)=>{
        if(!cartDropdown.classList.contains('open')) return;
        if(e.target.closest('#cartDropdown') || e.target.closest('#cartBtn')) return;
        setCartOpen(false);
      });
      document.addEventListener('keydown', (e)=>{ if(e.key==='Escape') setCartOpen(false); });
    }
  }
  
  // Navigate from cart dropdown CTA and wishlist dropdown CTA
  document.addEventListener('click', (e)=>{
    const cartViewBtn = e.target.closest('#cartDropdown .dropdown-footer .view-btn');
    if(cartViewBtn){ e.preventDefault(); window.location.href = 'cart.html'; return; }
    const wishViewBtn = e.target.closest('#wishlistDropdown .dropdown-footer .view-btn');
    if(wishViewBtn){ e.preventDefault(); window.location.href = 'wishlist.html'; return; }
  });

  // ================= Wishlist Logic (mirrors cart design but simplified) =================
  const WL_KEY='hub_wishlist_v1';
  function getWishlist(){ 
    // Return empty wishlist if not logged in
    if (!isUserLoggedIn()) return [];
    
    const key = getUserSpecificKey(WL_KEY);
    try{
      return JSON.parse(localStorage.getItem(key)||'[]');
    }catch(e){
      console.error(e);
      return[];
    } 
  }
  function saveWishlist(w){
    // Don't save if not logged in
    if (!isUserLoggedIn()) {
      console.warn('Cannot save wishlist: user not logged in');
      return;
    }
    
    const key = getUserSpecificKey(WL_KEY);
    try { localStorage.setItem(key, JSON.stringify(w)); } catch(e){ console.error(e); }
    // Emit wishlist updated event for global UI sync
    try { window.dispatchEvent(new CustomEvent('wishlist:updated', { detail:{ wishlist:w } })); } catch(e) {}
  }
  function findWishlistItem(w,title){ return w.find(i=>i.title===title); }

  function addToWishlistFromButton(btn){ 
    // Check authentication first
    if (!isUserLoggedIn()) {
      if (window.notify) {
        window.notify.warning('Please log in to add items to your wishlist.');
      }
      setTimeout(() => {
        window.location.href = 'loginregister.html';
      }, 1500);
      return;
    }
    
    if(!btn) return; 
    
    // Get product data
    let title=btn.getAttribute('data-product')||''; 
    const card=btn.closest('.product-card,.arrival-product-card,.card-back')||document.createElement('div'); 
    if(!title){ 
      const h=card.querySelector('h4,h3'); 
      title=h?h.textContent.trim():'Unknown product'; 
    }
    
    let price=normalizePrice(btn.getAttribute('data-price')); 
    if(!price){ 
      const pt=card.querySelector('.price-tag,.product-price,.price'); 
      if(pt) price=normalizePrice(pt.textContent); 
    }
    
    const imgEl=card.querySelector('img'); 
    const img=imgEl?imgEl.src:''; 
    const descEl=card.querySelector('.product-info p, p'); 
    const desc=descEl?descEl.textContent.trim():''; 
    const variant=btn.getAttribute('data-variant')||'';
    const productId = btn.getAttribute('data-product-id') || 0;
    
    // Save to backend API
    const token = localStorage.getItem('hub_access_token');
    if (token && productId) {
      fetch(`${window.SUPABASE_COMMERCE_API}/wishlist/${productId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          console.log('✅ Added to wishlist on backend');
          updateWishlistBadge();
          showToast(`${title} added to wishlist`);
        } else {
          console.warn('⚠️ Backend error:', data.message);
          // Fallback to localStorage
          addToLocalWishlist(title, price, img, desc, variant);
        }
      })
      .catch(error => {
        console.error('❌ Error adding to wishlist:', error);
        // Fallback to localStorage
        addToLocalWishlist(title, price, img, desc, variant);
      });
    } else {
      // Fallback to localStorage if no token or product ID
      addToLocalWishlist(title, price, img, desc, variant);
    }
  }
  
  // Helper function for localStorage fallback
  function addToLocalWishlist(title, price, img, desc, variant) {
    const wl=getWishlist(); 
    const existing=findWishlistItem(wl,title); 
    if(existing){ 
      existing.quantity=(existing.quantity||1)+1; 
      existing.timestamp=Date.now(); 
    } else { 
      wl.push({title,price,img,desc,quantity:1,variant,timestamp:Date.now()}); 
    }
    saveWishlist(wl); 
    updateWishlistBadge(); 
    showToast(`${title} added to wishlist`);
  }

  function removeFromWishlistByIndex(idx){ const wl=getWishlist(); if(idx<0||idx>=wl.length) return; wl.splice(idx,1); saveWishlist(wl); renderWishlistPage(); updateWishlistBadge(); }

  function moveSelectedWishlistToCart(selectedIdxs){ if(!selectedIdxs.length) return alert('No wishlist items selected'); const wl=getWishlist(); const cart=getCart(); selectedIdxs.forEach(i=>{ const it=wl[i]; if(!it) return; const existing=findItem(cart,it.title); if(existing){ existing.quantity=(existing.quantity||1)+ (it.quantity||1); } else { cart.push({title:it.title,price:it.price,img:it.img,desc:it.desc,quantity:(it.quantity||1),seller:'Wishlist'}); } wl.splice(i,1); }); saveCart(cart); saveWishlist(wl); updateBadges(); renderCartDropdown(); showToast('Selected items moved to cart'); }
  function moveSelectedCartItemsToWishlist(selectedIdxs){ if(!selectedIdxs.length) return alert('No cart items selected'); const cart=getCart(); const wl=getWishlist(); selectedIdxs.forEach(i=>{ const it=cart[i]; if(!it) return; const existing=findWishlistItem(wl,it.title); if(existing){ existing.quantity=(existing.quantity||1)+ (it.quantity||1); existing.timestamp=Date.now(); } else { wl.push({title:it.title,price:it.price,img:it.img,desc:it.desc,quantity:(it.quantity||1),variant:'',timestamp:Date.now()}); } }); // remove from cart in descending order
    selectedIdxs.sort((a,b)=>b-a).forEach(i=>{ if(i>=0&&i<cart.length) cart.splice(i,1); });
    saveCart(cart); saveWishlist(wl); updateBadges(); renderCartDropdown(); renderWishlistDropdown(); showToast('Selected cart items moved to wishlist'); }

  function renderWishlistPage(){ const wl=getWishlist(); const itemsEl=Q('#wishlistItems'); const emptyEl=Q('#emptyWishlist'); if(!itemsEl||!emptyEl) return; if(!wl.length){ itemsEl.style.display='none'; emptyEl.hidden=false; updateWishlistBadge(); const bar=Q('#wishlistFooterBar'); if(bar) bar.hidden=true; return; }
    itemsEl.style.display='flex'; emptyEl.hidden=true; updateWishlistBadge(); const html=wl.map((it,idx)=>{ const oldPrice=Math.round((it.price||0)*1.10); const savedPer=(oldPrice-(it.price||0))*(it.quantity||1); return `<div class="wishlist-item" data-index="${idx}"><div class="wi-col wi-check"><input type="checkbox" class="wl-check" data-index="${idx}"></div><div class="wi-col wi-product"><img src="${it.img}" alt="${it.title}" class="wishlist-item-img"><div class="wi-info"><h3 class="wi-title">${it.title}</h3><p class="wi-desc">${it.desc||''}</p><p class="wi-variant" data-action="edit-variant" data-index="${idx}">${it.variant? 'Variant: '+it.variant : 'Add variant'}</p></div></div><div class="wi-col wi-qty"><div class="quantity-control" role="group" aria-label="Wishlist quantity controls"><button class="quantity-btn" data-action="wl-decrease" data-index="${idx}" aria-label="Decrease quantity">-</button><span class="quantity-value" aria-live="polite">${it.quantity||1}</span><button class="quantity-btn" data-action="wl-increase" data-index="${idx}" aria-label="Increase quantity">+</button></div></div><div class="wi-col wi-price"><span class="price-old" style="color:#999;text-decoration:line-through;font-size:0.85rem">${PESO}${oldPrice}</span><span class="wi-price-now">${PESO}${it.price}</span>${savedPer>0? `<span class="wi-saved">Saved ${PESO}${savedPer}</span>`:''}</div><div class="wi-col wi-actions"><button class="btn-wish-add" data-action="add-cart" data-index="${idx}" aria-label="Add to cart">Add</button><button class="btn-wish-remove" data-action="remove" data-index="${idx}" aria-label="Remove">Delete</button></div></div>`; }).join(''); itemsEl.innerHTML=html; updateWishlistSummary(); wireWishlistSelection(); }

  function updateWishlistSummary(){ const wl=getWishlist(); const itemsEl=Q('#wishlistItems'); const bar=Q('#wishlistFooterBar'); if(!itemsEl||!bar) return; const selectedIdxs=Array.from(itemsEl.querySelectorAll('.wl-check:checked')).map(cb=>Number(cb.getAttribute('data-index'))); const selectedItems=selectedIdxs.map(i=>wl[i]).filter(Boolean); const total=selectedItems.reduce((s,it)=>s+((it.price||0)*(it.quantity||1)),0); const savings=selectedItems.reduce((s,it)=>{ const oldPrice=Math.round((it.price||0)*1.10); return s+((oldPrice-(it.price||0))*(it.quantity||1)); },0); const qty=selectedItems.reduce((s,it)=>s+(it.quantity||1),0); const allCount=Q('#wishlistAllCount'); const selQtyEl=Q('#wishlistSelectedQty'); const selValue=Q('#wishlistSelectedValue'); const savedEl=Q('#wishlistSaved'); const savedVal=Q('#wishlistSavedValue'); if(allCount) allCount.textContent=wl.length; if(selQtyEl) selQtyEl.textContent=qty; if(selValue) selValue.textContent=PESO+total; if(savedEl && savedVal){ if(savings>0){ savedEl.hidden=false; savedVal.textContent=PESO+savings; } else { savedEl.hidden=true; } } bar.hidden=!wl.length; }

  function wireWishlistSelection(){ const itemsEl=Q('#wishlistItems'); if(!itemsEl) return; const selAll=Q('#wishlistSelectAll'); const footSel=Q('#wishlistFooterSelectAll'); const delBtn=Q('#wishlistDelete'); const addSelectedBtn=Q('#wishlistAddSelected'); const clearBtn=Q('#wishlistClearAll'); function itemChecks(){ return Array.from(itemsEl.querySelectorAll('.wl-check')); }
    function syncGlobal(){ const items=itemChecks(); const all=items.length && items.every(i=>i.checked); if(selAll) selAll.checked=all; if(footSel) footSel.checked=all; }
    function setAll(state){ itemChecks().forEach(cb=>cb.checked=state); syncGlobal(); updateWishlistSummary(); }
    itemsEl.addEventListener('change',e=>{ if(e.target.classList.contains('wl-check')){ syncGlobal(); updateWishlistSummary(); } });
    if(selAll) selAll.addEventListener('change',e=>setAll(e.target.checked)); if(footSel) footSel.addEventListener('change',e=>setAll(e.target.checked));
  if(delBtn) delBtn.addEventListener('click',()=>{ const selected=itemChecks().filter(c=>c.checked).map(c=>Number(c.getAttribute('data-index'))).sort((a,b)=>b-a); if(!selected.length) return alert('No items selected'); const wl=getWishlist(); selected.forEach(i=>{ if(i>=0&&i<wl.length) wl.splice(i,1); }); saveWishlist(wl); renderWishlistPage(); });
  if(clearBtn) clearBtn.addEventListener('click',()=>{ if(!confirm('Clear entire wishlist?')) return; saveWishlist([]); renderWishlistPage(); renderWishlistDropdown(); });
    if(addSelectedBtn) addSelectedBtn.addEventListener('click',()=>{ const selected=itemChecks().filter(c=>c.checked).map(c=>Number(c.getAttribute('data-index'))); moveSelectedWishlistToCart(selected); renderWishlistPage(); });
    itemsEl.addEventListener('click',e=>{ const actBtn=e.target.closest('[data-action]'); if(!actBtn) return; const idx=Number(actBtn.getAttribute('data-index')); if(idx<0) return; const act=actBtn.getAttribute('data-action'); if(act==='remove') removeFromWishlistByIndex(idx); if(act==='add-cart'){ moveSelectedWishlistToCart([idx]); renderWishlistPage(); } if(act==='wl-increase'){ updateWishlistQuantityByIndex(idx,1); } if(act==='wl-decrease'){ updateWishlistQuantityByIndex(idx,-1); } if(act==='edit-variant'){ const wl=getWishlist(); const item=wl[idx]; if(!item) return; const newVar=prompt('Enter variant (leave blank to remove):', item.variant||''); if(newVar!==null){ item.variant=newVar.trim(); saveWishlist(wl); renderWishlistPage(); renderWishlistDropdown(); } }
    });
  }
  function updateWishlistQuantityByIndex(idx,chg){ const wl=getWishlist(); const item=wl[idx]; if(!item) return; item.quantity=(item.quantity||1)+chg; if(item.quantity<=0) wl.splice(idx,1); saveWishlist(wl); renderWishlistPage(); updateWishlistBadge(); }

  function initWishlist(){ 
    // Clear unauthenticated data
    clearUnauthenticatedData();
    
    // Only update badges and render if logged in
    updateWishlistBadge(); 
    if(Q('#wishlistItems')) renderWishlistPage(); 
  }

  // Wishlist Add-to-Cart preview dropdown logic (only on wishlist page)
  function renderWishlistAddPreviewDropdown(){ const dd=Q('#wishlistAddDropdown'); if(!dd) return; const itemsEl=Q('#wishlistItems'); if(!itemsEl) return; const wl=getWishlist(); const selectedIdxs=Array.from(itemsEl.querySelectorAll('.wl-check:checked')).map(cb=>Number(cb.getAttribute('data-index'))); if(!selectedIdxs.length){ dd.innerHTML='<div class="dropdown-header">Add to Cart Preview</div><div style="padding:18px;color:#666">No items selected</div>'; return; }
    const selectedItems=selectedIdxs.map(i=>wl[i]).filter(Boolean); const list=selectedItems.map(it=>`<div class="dropdown-item"><img src="${it.img||'https://source.unsplash.com/60x60/?food'}" alt="${it.title}" loading="lazy"><div class="item-details"><p class="item-name">${it.title}</p><p class="item-price">${PESO}${it.price} × ${it.quantity||1}</p></div></div>`).join(''); const total=selectedItems.reduce((s,it)=>s+((it.price||0)*(it.quantity||1)),0); dd.innerHTML=`<div class="dropdown-header">Add to Cart Preview</div><div class="dropdown-items" style="max-height:300px;overflow-y:auto">${list}</div><div class="dropdown-footer"><p class="items-count">Total: ${PESO}${total}</p><button class="view-btn" id="wishlistConfirmAdd">Confirm Add (${selectedItems.length})</button></div>`; }

  document.addEventListener('DOMContentLoaded',()=>{ if(document.body.classList.contains('wishlist-page')){ const previewBtn=Q('#wishlistAddPreview'); const panel=Q('#wishlistAddDropdown'); if(previewBtn && panel){ previewBtn.addEventListener('click',(e)=>{ e.preventDefault(); if(panel.hidden){ renderWishlistAddPreviewDropdown(); panel.hidden=false; panel.classList.add('open'); } else { panel.hidden=true; panel.classList.remove('open'); } }); document.addEventListener('click', (e)=>{ if(!panel.hidden && !panel.contains(e.target) && e.target!==previewBtn){ panel.hidden=true; panel.classList.remove('open'); } }); document.addEventListener('keydown',(e)=>{ if(e.key==='Escape' && !panel.hidden){ panel.hidden=true; panel.classList.remove('open'); } }); panel.addEventListener('click',(e)=>{ const confirmBtn=e.target.closest('#wishlistConfirmAdd'); if(confirmBtn){ const itemsEl=Q('#wishlistItems'); if(!itemsEl) return; const selected=Array.from(itemsEl.querySelectorAll('.wl-check:checked')).map(cb=>Number(cb.getAttribute('data-index'))); moveSelectedWishlistToCart(selected); panel.hidden=true; panel.classList.remove('open'); renderWishlistPage(); } }); } } });

  // Extend cart selection controls with move to wishlist button
  document.addEventListener('DOMContentLoaded',()=>{
    const moveBtn=document.getElementById('footerMoveWishlist');
    if(moveBtn){ moveBtn.addEventListener('click',()=>{
      const cont=Q('#cartItems'); if(!cont) return; const selected=Array.from(cont.querySelectorAll('.item-check:checked')).map(cb=>Number(cb.getAttribute('data-index'))); if(!selected.length){ alert('No cart items selected'); return; }
      moveSelectedCartItemsToWishlist(selected); renderCartPage(); renderWishlistPage(); updateWishlistBadge(); }); }
  });

  window.hubCart={ getCart, saveCart, addToCartFromButton, renderCartPage, updateSummary, checkout };
  window.hubWishlist={ getWishlist, saveWishlist, renderWishlistPage, addToWishlistFromButton };
  
  // Debug helper: manually clear all cart/wishlist data (accessible from console)
  window.clearAllCartWishlistData = function() {
    Object.keys(localStorage).forEach(key => {
      if (key.includes('hub_cart') || key.includes('hub_wishlist')) {
        localStorage.removeItem(key);
        console.log('Cleared:', key);
      }
    });
    console.log('✅ All cart and wishlist data cleared');
    // Refresh UI
    updateBadges();
    updateWishlistBadge();
    renderCartDropdown();
    renderWishlistDropdown();
    if(Q('#cartItems')) renderCartPage();
    if(Q('#wishlistItems')) renderWishlistPage();
  };

  // Global listeners for automatic UI refresh when storage changes via saveCart/saveWishlist
  window.addEventListener('cart:updated', (e)=>{
    // Refresh badges
    updateBadges();
    // Refresh dropdown only if it's present & open
    const cd=Q('#cartDropdown'); if(cd && cd.classList.contains('open')){ try{ renderCartDropdown(); }catch(_){} }
    // If cart page content exists, update summary counts (non-destructive)
    if(Q('#cartItems')){ updateSummary(); }
  });
  window.addEventListener('wishlist:updated', (e)=>{
    updateWishlistBadge();
    const wd=Q('#wishlistDropdown'); if(wd && wd.classList.contains('open')){ try{ renderWishlistDropdown(); }catch(_){} }
    // If wishlist page present, refresh summary bar (renderWishlistPage handles full rebuild elsewhere)
    if(Q('#wishlistItems')){ updateWishlistSummary(); }
  });

  document.addEventListener('DOMContentLoaded', ()=>{ 
    // SKIP cleanup on auth pages
    const currentPath = window.location.pathname.toLowerCase();
    const isAuthPage = currentPath.includes('loginregister') || 
                      currentPath.includes('login.html') || 
                      currentPath.includes('register.html');
    
    if (!isAuthPage && !isUserLoggedIn()) {
      console.log('🔍 DOMContentLoaded: Forcing cart/wishlist clear (not logged in)');
      clearUnauthenticatedData();
      // Force empty arrays in localStorage to override any cached values
      localStorage.setItem('hub_cart_v1', JSON.stringify([]));
      localStorage.setItem('hub_wishlist_v1', JSON.stringify([]));
    }
    
    initNavbarFeatures(); 
    initCart(); 
    initWishlist(); 
    initCheckoutModal(); 
  });

  // Delegated sidebar navigation handler: if inline handlers fail, this will
  // intercept clicks on `.nav-link` and call the page's `switchSection` function
  document.addEventListener('DOMContentLoaded', ()=>{
    const labelMap = {
      'returns & refunds':'returns',
      'returns&refunds':'returns',
      'dashboard':'dashboard',
      'active deliveries':'deliveries',
      'deliveries':'deliveries',
      'live tracking':'tracking',
      'live map':'tracking',
      'earnings':'earnings',
      'delivery history':'history',
      'history':'history',
      'statistics':'stats',
      'profile':'profile',
      'sellers':'sellers',
      'riders':'riders',
      'reports':'reports',
      'orders':'orders',
      'products':'products',
      'settings':'settings',
      'reviews':'reviews',
      'sales approvals':'sales',
      'sales':'sales'
    };

    document.body.addEventListener('click', (e)=>{
      const link = e.target.closest && e.target.closest('.nav-link');
      if(!link) return;
      // prevent default navigation to '#'
      e.preventDefault();

      const explicit = link.getAttribute('data-section');
      const label = (explicit || link.getAttribute('data-label') || '').toLowerCase().trim();
      const sectionName = explicit || (labelMap[label] || label.replace(/\s/g,''));

      if(typeof window.switchSection === 'function'){
        try { window.switchSection(sectionName, e); } catch(err){ console.error('switchSection error', err); }
      }
    }, true);
  });

  // Product Quick-View Modal
  function initProductModal(){
    const modal=Q('#productModal'); if(!modal) return;
    const overlay=modal.querySelector('.modal-overlay');
    const closeBtn=modal.querySelector('.modal-close');
    const imgEl=modal.querySelector('.modal-img');
    const titleEl=modal.querySelector('.modal-title');
    const priceEl=modal.querySelector('.modal-price');
    const descEl=modal.querySelector('.modal-desc');
    const addBtn=modal.querySelector('.modal-add-btn');
    
    // Safety check - if required elements don't exist, skip modal initialization
    if(!titleEl || !priceEl || !descEl) return;

    function open(info){
      titleEl.textContent=info.title||'';
      priceEl.textContent=info.price||'';
      descEl.textContent=info.desc||'';
      if(imgEl && info.img) imgEl.src=info.img;
      if(addBtn){ addBtn.setAttribute('data-product', info.title||''); addBtn.setAttribute('data-price', info.price||''); }
      modal.hidden=false; document.body.style.overflow='hidden';
    }
    function closeModal(){ modal.hidden=true; document.body.style.overflow=''; }

    // Close handlers
    if(overlay) overlay.addEventListener('click', closeModal);
    if(closeBtn) closeBtn.addEventListener('click', closeModal);
    document.addEventListener('keydown', (e)=>{ if(e.key==='Escape' && !modal.hidden) closeModal(); });

    // Delegate view button clicks to open modal
    document.addEventListener('click', (e)=>{
      const v = e.target.closest('.btn-view-circle');
      if(!v) return;
      e.preventDefault();
      const card = v.closest('.product-shop-card, .product-card');
      const title = v.getAttribute('data-product') || (card && (card.querySelector('.product-shop-title')||card.querySelector('h3')||card.querySelector('h4'))?.textContent.trim()) || 'Product';
      const price = v.getAttribute('data-price') || (card && card.querySelector('.price-current')?.textContent.trim()) || '';
      const img = card && (card.querySelector('img')?.src);
      const desc = card && (card.querySelector('.product-shop-unit')?.textContent.trim() || '');
      open({ title, price, img, desc });
    });

    // Add to cart from modal
    if(addBtn) addBtn.addEventListener('click', (e)=>{ e.preventDefault(); addToCartFromButton(addBtn); closeModal(); });
  }

  document.addEventListener('DOMContentLoaded', ()=>{ initProductModal(); });

  // Global navbar search handler (redirects to shop.html?search=...)
  // Works on all pages with navbar search bars
  document.addEventListener('DOMContentLoaded', () => {
    try {
      // Clean up any previous search highlights on page load
      document.querySelectorAll('.search-highlight').forEach(el => {
        el.classList.remove('search-highlight');
      });
      
      // Remove any existing "no results" messages
      const existingMsg = document.getElementById('searchNoResultsMessage');
      if (existingMsg) {
        existingMsg.remove();
      }
      
      // Find all navbars with search bars (in case there are multiple)
      const navbars = document.querySelectorAll('.navbar');
      
      navbars.forEach(navbar => {
        const searchBar = navbar.querySelector('.search-bar');
        if (!searchBar) return;
        
        const input = searchBar.querySelector('input');
        const button = searchBar.querySelector('button');
        
        if (!input || !button) return;
        
        // Skip if this is seller.html's search bar (it has its own handler)
        // seller.html handles its own search functionality
        if (input.id === 'navbarSearch' && document.getElementById('navbarSearchBtn')) {
          // seller.html has its own search handler - skip global handler
          // But still prefill from URL if present (not from localStorage)
          try {
            const params = new URLSearchParams(window.location.search);
            const searchQuery = (params.get('search') || params.get('q') || '').trim();
            if (searchQuery && input && !input.value) {
              input.value = searchQuery;
            } else {
              // Reset search bar on page load (don't keep previous search)
              input.value = '';
            }
          } catch(e) { /* ignore */ }
          return;
        }
        
        // Create autocomplete dropdown container
        const autocompleteContainer = document.createElement('div');
        autocompleteContainer.className = 'search-autocomplete';
        autocompleteContainer.style.cssText = `
          position: absolute;
          top: 100%;
          left: 0;
          right: 0;
          background: white;
          border: 1px solid #ddd;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          max-height: 300px;
          overflow-y: auto;
          z-index: 1000;
          display: none;
          margin-top: 5px;
        `;
        searchBar.style.position = 'relative';
        searchBar.appendChild(autocompleteContainer);
        
        let suggestionTimeout = null;
        let selectedIndex = -1;

        // Function to search for products on current page
        const searchProductsOnPage = (searchTerm) => {
          const searchLower = searchTerm.toLowerCase();
          
          // Find all product containers on different pages
          const productContainers = [
            document.getElementById('productsGrid'),           // shop.html
            document.getElementById('sellerProductsGrid'),     // seller.html
            document.getElementById('bestsellerProductsGrid'), // index.html
          ].filter(Boolean);
          
          if (productContainers.length === 0) {
            return null; // No product containers found
          }
          
          // Find all product cards
          const allProductCards = [];
          productContainers.forEach(container => {
            const cards = container.querySelectorAll('.product-shop-card, .product-card-packshot');
            allProductCards.push(...Array.from(cards));
          });
          
          if (allProductCards.length === 0) {
            return null; // No products on page
          }
          
          // Search for matching products
          const matches = [];
          allProductCards.forEach(card => {
            // Get product title from card
            const titleEl = card.querySelector('.product-shop-title, h3, h4');
            const title = titleEl ? titleEl.textContent.toLowerCase() : '';
            
            // Get product description if available
            const descEl = card.querySelector('.product-shop-seller, p');
            const description = descEl ? descEl.textContent.toLowerCase() : '';
            
            // Check if search term matches
            if (title.includes(searchLower) || description.includes(searchLower)) {
              matches.push(card);
            }
          });
          
          return matches;
        };
        
        // Function to highlight and scroll to product
        const highlightAndScrollToProduct = (productCard) => {
          if (!productCard) return;
          
          // Remove previous highlights
          document.querySelectorAll('.search-highlight').forEach(el => {
            el.classList.remove('search-highlight');
          });
          
          // Add highlight class
          productCard.classList.add('search-highlight');
          
          // Scroll to product with offset for navbar
          const navbarHeight = document.querySelector('.navbar')?.offsetHeight || 80;
          const cardPosition = productCard.getBoundingClientRect().top + window.pageYOffset;
          const offsetPosition = cardPosition - navbarHeight - 20;
          
          window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
          });
          
          // Remove highlight after animation completes (3 seconds)
          setTimeout(() => {
            productCard.classList.remove('search-highlight');
          }, 3000);
        };
        
        // Function to show "No products found" message
        const showNoProductsMessage = (searchTerm) => {
          // Remove any existing messages
          const existingMsg = document.getElementById('searchNoResultsMessage');
          if (existingMsg) {
            existingMsg.remove();
          }
          
          // Create message element
          const message = document.createElement('div');
          message.id = 'searchNoResultsMessage';
          message.style.cssText = `
            position: fixed;
            top: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: #e74c3c;
            color: white;
            padding: 16px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            font-size: 14px;
            font-weight: 500;
            animation: fadeInOut 4s ease-out forwards;
          `;
          message.textContent = `No matching products found.`;
          
          // Add fade animation
          if (!document.getElementById('searchMessageStyles')) {
            const style = document.createElement('style');
            style.id = 'searchMessageStyles';
            style.textContent = `
              @keyframes fadeInOut {
                0% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
                15% { opacity: 1; transform: translateX(-50%) translateY(0); }
                85% { opacity: 1; transform: translateX(-50%) translateY(0); }
                100% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
              }
            `;
            document.head.appendChild(style);
          }
          
          document.body.appendChild(message);
          
          // Remove message after animation
          setTimeout(() => {
            if (message.parentNode) {
              message.remove();
            }
          }, 4000);
        };
        
        const doSearch = () => {
          const term = (input?.value || '').trim();
          if (!term || term.length < 2) {
            if (input) input.setAttribute('placeholder', 'Type at least 2 characters...');
            return;
          }
          
          // Close autocomplete
          autocompleteContainer.style.display = 'none';
          
          // Check if we're on index.html - always redirect to shop.html
          const isIndexPage = window.location.pathname.includes('index.html') || 
                             window.location.pathname === '/' || 
                             window.location.pathname.endsWith('/');
          
          if (isIndexPage) {
            // From index.html, always redirect to shop.html with search
            window.location.href = `shop.html?search=${encodeURIComponent(term)}`;
            return;
          }
          
          // First, try to search on current page
          const matches = searchProductsOnPage(term);
          
          if (matches && matches.length > 0) {
            // Found matches on current page - highlight and scroll to first match
            highlightAndScrollToProduct(matches[0]);
            
            // If multiple matches, log count (optional: could show a counter)
            if (matches.length > 1) {
              console.log(`Found ${matches.length} products matching "${term}"`);
            }
          } else if (matches === null) {
            // No product containers on this page - redirect to shop.html
            window.location.href = `shop.html?search=${encodeURIComponent(term)}`;
          } else {
            // Product containers exist but no matches - show message
            showNoProductsMessage(term);
          }
        };

        // Function to load autocomplete suggestions
        const loadSuggestions = async (query) => {
          if (query.length < 2) {
            autocompleteContainer.style.display = 'none';
            return;
          }
          
          try {
            const productApiBase = window.SUPABASE_PRODUCT_API || window.location.origin;
            const response = await fetch(`${productApiBase}/products/suggestions?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.success && data.data && data.data.length > 0) {
              autocompleteContainer.innerHTML = '';
              data.data.forEach((suggestion, index) => {
                const item = document.createElement('div');
                item.className = 'autocomplete-item';
                item.style.cssText = `
                  padding: 12px 16px;
                  cursor: pointer;
                  border-bottom: 1px solid #f0f0f0;
                  transition: background-color 0.2s;
                `;
                item.innerHTML = `
                  <div style="font-weight: 500; color: #2F5233;">${escapeHtml(suggestion.title)}</div>
                  ${suggestion.category ? `<div style="font-size: 12px; color: #666; margin-top: 2px;">${escapeHtml(suggestion.category)}</div>` : ''}
                `;
                
                item.addEventListener('mouseenter', () => {
                  item.style.backgroundColor = '#f8f9fa';
                  selectedIndex = index;
                });
                
                item.addEventListener('mouseleave', () => {
                  item.style.backgroundColor = 'transparent';
                });
                
                item.addEventListener('click', () => {
                  input.value = suggestion.title;
                  autocompleteContainer.style.display = 'none';
                  doSearch();
                });
                
                autocompleteContainer.appendChild(item);
              });
              
              autocompleteContainer.style.display = 'block';
              selectedIndex = -1;
            } else {
              autocompleteContainer.style.display = 'none';
            }
          } catch (error) {
            console.warn('Error loading suggestions:', error);
            autocompleteContainer.style.display = 'none';
          }
        };
        
        // Helper function to escape HTML
        const escapeHtml = (text) => {
          const div = document.createElement('div');
          div.textContent = text || '';
          return div.innerHTML;
        };
        
        // Prefill search input ONLY from URL (not from localStorage)
        // This ensures search bar resets on page refresh
        try {
          const params = new URLSearchParams(window.location.search);
          // Support both 'search' and 'q' for backward compatibility
          const searchQuery = (params.get('search') || params.get('q') || '').trim();
          if (searchQuery && input) {
            input.value = searchQuery;
            input.setAttribute('placeholder', '');
          } else {
            // Reset search bar on page load (don't keep previous search)
            input.value = '';
          }
        } catch(e) { /* ignore */ }

        // Add event listeners (only if not already added)
        if (!button.dataset.globalSearchHandler) {
          button.dataset.globalSearchHandler = 'true';
          button.addEventListener('click', (e) => { 
            e.preventDefault(); 
            e.stopPropagation();
            autocompleteContainer.style.display = 'none';
            doSearch(); 
          });
        }
        
        if (!input.dataset.globalSearchHandler) {
          input.dataset.globalSearchHandler = 'true';
          
          // Autocomplete on input
          input.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            clearTimeout(suggestionTimeout);
            
            if (query.length >= 2) {
              suggestionTimeout = setTimeout(() => {
                loadSuggestions(query);
              }, 300); // Debounce 300ms
            } else {
              autocompleteContainer.style.display = 'none';
            }
          });
          
          // Handle keyboard navigation in autocomplete
          input.addEventListener('keydown', (e) => {
            const items = autocompleteContainer.querySelectorAll('.autocomplete-item');
            
            if (e.key === 'ArrowDown') {
              e.preventDefault();
              selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
              if (items[selectedIndex]) {
                items[selectedIndex].scrollIntoView({ block: 'nearest' });
                items.forEach((item, idx) => {
                  item.style.backgroundColor = idx === selectedIndex ? '#f8f9fa' : 'transparent';
                });
              }
            } else if (e.key === 'ArrowUp') {
              e.preventDefault();
              selectedIndex = Math.max(selectedIndex - 1, -1);
              items.forEach((item, idx) => {
                item.style.backgroundColor = idx === selectedIndex ? '#f8f9fa' : 'transparent';
              });
            } else if (e.key === 'Enter') {
              e.preventDefault();
              e.stopPropagation();
              
              if (selectedIndex >= 0 && items[selectedIndex]) {
                // Select highlighted suggestion
                input.value = items[selectedIndex].querySelector('div').textContent;
                autocompleteContainer.style.display = 'none';
                doSearch();
              } else {
                // Perform search with current input
                autocompleteContainer.style.display = 'none';
                doSearch();
              }
            } else if (e.key === 'Escape') {
              autocompleteContainer.style.display = 'none';
              selectedIndex = -1;
            }
          });
        }
        
        // Close autocomplete when clicking outside
        document.addEventListener('click', (e) => {
          if (!searchBar.contains(e.target)) {
            autocompleteContainer.style.display = 'none';
            selectedIndex = -1;
          }
        });
      });
    } catch (e) {
      console.warn('Search bar init failed', e);
    }
  });

  // Checkout Modal Functionality
  function initCheckoutModal(){
    const modal=Q('#checkoutModal');
    if(!modal) return;
    
    const overlay=modal.querySelector('.modal-overlay');
    const closeBtn=modal.querySelector('.modal-close');
    const closeBtnAlt=modal.querySelector('.modal-close-btn');
    const form=Q('#checkoutForm');
    
    function closeModal(){
      modal.hidden=true;
      document.body.style.overflow='';
      if(form) form.reset();
    }
    
    // Close modal handlers
    if(overlay) overlay.addEventListener('click',closeModal);
    if(closeBtn) closeBtn.addEventListener('click',closeModal);
    if(closeBtnAlt) closeBtnAlt.addEventListener('click',closeModal);
    
    // Escape key
    document.addEventListener('keydown',(e)=>{
      if(e.key==='Escape' && !modal.hidden) closeModal();
    });
    
    // Form submission - only handle if not already handled by cart.html
    if(form){
      // Check if we're on cart.html (which has its own handler)
      const isCartPage = window.location.pathname.includes('cart.html');
      
      form.addEventListener('submit',async (e)=>{
        // If on cart.html, let cart.html handle it (it will prevent default)
        if(isCartPage) {
          return; // cart.html will handle the submission
        }
        
        e.preventDefault();
        
        const name=Q('#checkoutName')?.value.trim();
        const phone=Q('#checkoutPhone')?.value.trim();
        const address=Q('#checkoutAddress')?.value.trim();
        const notes=Q('#checkoutNotes')?.value.trim();
        
        if(!name || !phone || !address){
          alert('Please fill in all required fields');
          return;
        }
        
        // Save checkout data to user profile (if function exists)
        if(typeof saveCheckoutDataToProfile === 'function'){
          await saveCheckoutDataToProfile();
        }
        
        // Get selected items
        const cart=getCart();
        const cont=Q('#cartItems');
        if(!cont) return;
        const selectedIdxs=Array.from(cont.querySelectorAll('.item-check:checked')).map(cb=>Number(cb.getAttribute('data-index')));
        const selectedItems=selectedIdxs.map(i=>cart[i]).filter(Boolean);
        
        // Create order summary
        const orderDetails={
          customer:{ name, phone, address, notes },
          items:selectedItems,
          payment:'Cash on Delivery',
          subtotal:selectedItems.reduce((s,i)=>s+((i.price||0)*(i.quantity||0)),0),
          delivery:50,
          timestamp:new Date().toISOString()
        };
        orderDetails.total=orderDetails.subtotal+orderDetails.delivery;
        
        // Send order to backend API for persistence and ERP integration
        console.log('Order placed:', orderDetails);
        try{
          const orderApiBase = window.SUPABASE_ORDER_API || window.location.origin;
          fetch(orderApiBase,{
            method:'POST',
            headers:{ 'Content-Type':'application/json' },
            body: JSON.stringify(orderDetails)
          }).then(r=>r.json()).then(j=>{
            if(j && j.success){
              showToast('Order successfully created (ID: '+j.order_id+')');
              // Remove ordered items from cart
              selectedIdxs.sort((a,b)=>b-a).forEach(i=>{ if(i>=0&&i<cart.length) cart.splice(i,1); });
              saveCart(cart);
              // Show success message
              alert(`Thank you, ${name}!\n\nYour order has been placed successfully.\nTotal: ${PESO}${orderDetails.total}\nPayment: Cash on Delivery\n\nWe'll contact you at ${phone} for delivery confirmation.`);
              closeModal(); renderCartPage(); updateBadges();
            } else {
              console.error('Order API response', j);
              alert('Order failed: '+(j && j.error ? j.error : 'Server error'));
            }
          }).catch(err=>{
            console.error('Order API error', err);
            alert('Order failed (network/server). Please try again.');
          });
        }catch(e){ console.error(e); alert('Order failed (client)'); }
      });
    }
  }
})();

// ============== Platform Name Utility ==============
async function loadPlatformName() {
    try {
        // Check localStorage first for quick access
        const cachedName = localStorage.getItem('platform_name');
        if (cachedName) {
            updatePlatformNameInUI(cachedName);
        }
        
        // Fetch from server to get latest
        const response = await fetch('/api/platform/name');
        if (response.ok) {
            const result = await response.json();
            if (result.success && result.data && result.data.platform_name) {
                const platformName = result.data.platform_name;
                localStorage.setItem('platform_name', platformName);
                updatePlatformNameInUI(platformName);
            }
        }
    } catch (error) {
        console.warn('Could not load platform name:', error);
        // Use default
        updatePlatformNameInUI('Hub');
    }
}

function updatePlatformNameInUI(platformName) {
    // Update page title
    const currentTitle = document.title;
    if (currentTitle.includes(' - ')) {
        document.title = platformName + currentTitle.substring(currentTitle.indexOf(' - '));
    } else if (currentTitle === 'Hub' || currentTitle.includes('Hub')) {
        document.title = currentTitle.replace(/Hub/g, platformName);
    }
    
    // Update navbar logos
    document.querySelectorAll('.logo a').forEach(el => {
        if (el.textContent.trim() === 'Hub') {
            el.textContent = platformName;
        }
    });
    
    // Update admin panel brand
    document.querySelectorAll('.sidebar-brand .brand-text').forEach(el => {
        if (el.textContent.trim() === 'Admin Panel' || el.textContent.trim() === 'Hub') {
            el.textContent = platformName;
        }
    });
}

// Load platform name on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadPlatformName);
} else {
    loadPlatformName();
}

// =============================================================
// Auth (Login & Registration) Logic (merged from auth.js)
// Scoped globally so inline handlers in loginregister.html keep working.
// Runs only on pages with body.auth.
// =============================================================
function switchForm(formType) {
  ['loginContainer','accountTypeContainer','customerContainer','sellerContainer','riderContainer']
    .forEach(id => { const el = document.getElementById(id); el && el.classList.remove('active'); });
  const map={ login:'loginContainer', accountType:'accountTypeContainer', customer:'customerContainer', seller:'sellerContainer', rider:'riderContainer' };
  if(map[formType]){ const t=document.getElementById(map[formType]); t && t.classList.add('active'); }
}
function selectAccountType(type){ if(type==='customer'){ switchForm('customer'); switchCustomerStep(1);} else if(type==='seller'){ loadSellerRegions(); switchForm('seller'); switchSellerStep(1);} else if(type==='rider'){ switchForm('rider'); switchRiderStep(1);} }
function switchSellerStep(step){ ['sellerForm1','sellerForm2','sellerForm3','sellerForm4'].forEach(id=>document.getElementById(id)?.classList.remove('active-step')); ['sellerStep1','sellerStep2','sellerStep3','sellerStep4'].forEach(id=>document.getElementById(id)?.classList.remove('active')); const f='sellerForm'+step; const s='sellerStep'+step; document.getElementById(f)?.classList.add('active-step'); document.getElementById(s)?.classList.add('active'); }
function switchRiderStep(step){ ['riderForm1','riderForm2','riderForm3','riderForm4'].forEach(id=>document.getElementById(id)?.classList.remove('active-step')); ['riderStep1','riderStep2','riderStep3','riderStep4'].forEach(id=>document.getElementById(id)?.classList.remove('active')); const f='riderForm'+step; const s='riderStep'+step; document.getElementById(f)?.classList.add('active-step'); document.getElementById(s)?.classList.add('active'); }
function switchCustomerStep(step){
  ['customerForm','customerFormOTP'].forEach(id=>document.getElementById(id)?.classList.remove('active-step'));
  ['customerStep1','customerStep2'].forEach(id=>document.getElementById(id)?.classList.remove('active'));
  if(step===2){
    document.getElementById('customerForm')?.classList.add('active-step');
    document.getElementById('customerStep1')?.classList.add('active');
  } else if(step===2){
    document.getElementById('customerFormOTP')?.classList.add('active-step');
    document.getElementById('customerStep2')?.classList.add('active');
  }
}
const pendingRegistrations={ customer:null, seller:null, rider:null };
function sendOTP(email,type){
  if(!email) return showError(type==='customer'?'custEmailError':'selEmailError','Missing email');
  fetch('/api/auth/send-otp',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ email: email, type: type })
  }).then(r=>r.json()).then(j=>{
    if(j && j.success){ showSuccess((type||'')+'Success', `OTP sent to ${email}`); if(type==='customer') switchCustomerStep(2); }
    else { showError(type==='customer'?'custEmailError':`${type}EmailError`, j && j.error ? j.error : 'Failed to send OTP'); switchCustomerStep(2); }
  }).catch(err=>{ console.error('sendOTP error',err); showError(type==='customer'?'custEmailError':`${type}EmailError`,'Server error'); });
}
function resendOTP(type){ const p=pendingRegistrations[type]; if(!p?.email){ showError(type==='customer'?'custOTPError':`${type}OTPError`,'No pending registration to resend OTP for.'); return;} sendOTP(p.email,type); }
const PSGC_API='https://psgc.gitlab.io/api'; let regionsCache={}, provincesCache={}, citiesCache={};
async function loadSellerRegions(){ const sel=document.getElementById('selRegion'); const load=document.getElementById('selRegionLoading'); if(!sel||sel.options.length>1) return; load?.classList.add('show'); try{ const res=await fetch(`${PSGC_API}/regions`); if(!res.ok) throw new Error('Failed'); const regions=await res.json(); regions.forEach(r=>{ const o=document.createElement('option'); o.value=r.code; o.textContent=r.name; sel.appendChild(o); regionsCache[r.code]=r; }); load?.classList.remove('show'); }catch(e){ console.error(e); if(load) load.innerHTML='<div class="error show">Failed to load regions</div>'; showError('selRegionError','Unable to load regions'); } }
async function loadSellerProvinces(){ const selR=document.getElementById('selRegion'); const selP=document.getElementById('selProvince'); const load=document.getElementById('selProvinceLoading'); const selC=document.getElementById('selCity'); if(!selR||!selP||!selC) return; selP.innerHTML='<option value="">Select Province</option>'; selP.disabled=true; selC.innerHTML='<option value="">Select City</option>'; selC.disabled=true; const code=selR.value; if(!code) return; load?.classList.add('show'); try{ if(provincesCache[code]){ populateSellerProvinces(provincesCache[code]); load?.classList.remove('show'); return;} const res=await fetch(`${PSGC_API}/regions/${code}/provinces`); if(!res.ok) throw new Error('Failed provinces'); const provinces=await res.json(); provincesCache[code]=provinces; populateSellerProvinces(provinces); load?.classList.remove('show'); }catch(e){ console.error(e); if(load) load.innerHTML='<div class="error show">Failed to load provinces</div>'; showError('selProvinceError','Unable to load provinces'); } }
function populateSellerProvinces(provinces){ const selP=document.getElementById('selProvince'); if(!selP) return; selP.innerHTML='<option value="">Select Province</option>'; provinces.forEach(p=>{ const o=document.createElement('option'); o.value=p.code; o.textContent=p.name; selP.appendChild(o); }); selP.disabled=false; }
async function loadSellerCities(){ const selP=document.getElementById('selProvince'); const selC=document.getElementById('selCity'); const load=document.getElementById('selCityLoading'); if(!selP||!selC) return; selC.innerHTML='<option value="">Select City</option>'; selC.disabled=true; const provinceCode=selP.value; if(!provinceCode) return; load?.classList.add('show'); try{ if(citiesCache[provinceCode]){ populateSellerCities(citiesCache[provinceCode]); load?.classList.remove('show'); return;} const [citiesRes, munRes]=await Promise.all([fetch(`${PSGC_API}/cities`), fetch(`${PSGC_API}/municipalities`)]); if(!citiesRes.ok||!munRes.ok) throw new Error('Failed cities'); const allCities=await citiesRes.json(); const allMun=await munRes.json(); const combined=[...allCities.filter(c=>c.provinceCode===provinceCode), ...allMun.filter(m=>m.provinceCode===provinceCode)]; citiesCache[provinceCode]=combined; populateSellerCities(combined); load?.classList.remove('show'); }catch(e){ console.error(e); if(load) load.innerHTML='<div class="error show">Failed to load cities</div>'; showError('selCityError','Unable to load cities'); } }
function populateSellerCities(cities){ const selC=document.getElementById('selCity'); if(!selC) return; selC.innerHTML='<option value="">Select City</option>'; if(!cities.length){ const o=document.createElement('option'); o.value=''; o.textContent='No cities available'; selC.appendChild(o); } else { cities.sort((a,b)=>a.name.localeCompare(b.name)); cities.forEach(c=>{ const o=document.createElement('option'); o.value=c.code; o.textContent=c.name; selC.appendChild(o); }); } selC.disabled=false; }
function validateEmail(e){ return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e); }
function validatePassword(p){ return p.length>=6; }
function showError(id,msg){ const el=document.getElementById(id); if(el){ el.textContent=msg; el.classList.add('show'); } }
function clearError(id){ const el=document.getElementById(id); if(el){ el.classList.remove('show'); el.textContent=''; } }
function showSuccess(id,msg){ const el=document.getElementById(id); if(el){ el.textContent=msg; el.classList.add('show'); setTimeout(()=>el.classList.remove('show'),5000); } }
function handleLogin(ev){ 
  ev.preventDefault(); 
  clearError('loginEmailError'); 
  clearError('loginPasswordError'); 
  const email=document.getElementById('loginEmail').value.trim(); 
  const password=document.getElementById('loginPassword').value; 
  let ok=true; 
  
  // Check for empty fields first
  if(!email || !password) {
    const errorMsg = 'Please fill in all required fields.';
    if(window.notify) {
      window.notify.warning(errorMsg);
    }
    if(!email) showError('loginEmailError', 'Email is required');
    if(!password) showError('loginPasswordError', 'Password is required');
    return;
  }
  
  if(!validateEmail(email)){ 
    const errorMsg = 'Please enter a valid email address.';
    showError('loginEmailError', errorMsg); 
    if(window.notify) {
      window.notify.error(errorMsg);
    }
    ok=false;
  } 
  if(!password){ 
    showError('loginPasswordError','Password is required'); 
    ok=false;
  } 
  if(ok){
    // Try Supabase Auth first (client-side) so deployed frontend can authenticate without local backend
    const SUPABASE_REF = 'sfeccfbdmbwoblixyoti';
    const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNmZWNjZmJkbWJ3b2JsaXh5b3RpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwODAwNTksImV4cCI6MjA5NTY1NjA1OX0.uM7DX7T-PQqPsMIwh-Fna1BUtVkkOhR4PiT2YqYlhIE';
    const supaUrl = `https://${SUPABASE_REF}.supabase.co/auth/v1/token?grant_type=password`;

    fetch(supaUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON,
        'Authorization': `Bearer ${SUPABASE_ANON}`
      },
      body: JSON.stringify({ email, password })
    })
    .then(r => r.json().then(resp => ({ status: r.status, resp })))
    .then(({ status, resp }) => {
      if (resp && resp.access_token) {
        // Supabase successful login
        localStorage.setItem('hub_access_token', resp.access_token);
        if (resp.refresh_token) localStorage.setItem('hub_refresh_token', resp.refresh_token);
        if(window.notify) window.notify.success('Login successful! Welcome back.');
        document.getElementById('loginForm').reset();

        // Decode role if present in user metadata
        let userRole = null;
        try { if (resp.user && resp.user.role) userRole = resp.user.role; } catch(e){}

        // Redirect by role or returnUrl
        const returnUrl = localStorage.getItem('returnUrl');
        if (returnUrl) { localStorage.removeItem('returnUrl'); window.location.href = returnUrl; return; }
        if (userRole === 'seller') window.location.href = '/seller_dashboard.html';
        else if (userRole === 'rider') window.location.href = '/rider_dashboard.html';
        else if (userRole === 'admin') window.location.href = '/admin_dashboard.html';
        else window.location.href = '/index.html';
        return;
      }

      // Fallback: try legacy backend endpoint if Supabase auth fails
      return fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})})
        .then(r=>{ const status = r.status; return r.json().then(resp => ({status, resp})); })
        .then(({status, resp})=>{
          if(resp && resp.success){
            if(resp.token) localStorage.setItem('hub_access_token', resp.token);
            if(resp.refresh_token) localStorage.setItem('hub_refresh_token', resp.refresh_token);
            if(window.notify) window.notify.success('Login successful! Welcome back.');
            document.getElementById('loginForm').reset();
            let userRole = null;
            if(resp.token){ try{ const parts = resp.token.split('.'); const decoded = JSON.parse(atob(parts[1])); userRole = decoded.role; }catch(e){}}
            const returnUrl = localStorage.getItem('returnUrl');
            if(returnUrl){ localStorage.removeItem('returnUrl'); window.location.href = returnUrl; return; }
            if(userRole==='seller') window.location.href='/seller_dashboard.html';
            else if(userRole==='rider') window.location.href='/rider_dashboard.html';
            else if(userRole==='admin') window.location.href='/admin_dashboard.html';
            else window.location.href='/index.html';
          } else {
            showError('loginPasswordError', (resp && (resp.error || resp.message)) || 'Login failed');
            if(window.notify) window.notify.error((resp && (resp.error || resp.message)) || 'Login failed');
          }
        }).catch(err=>{ console.error('fallback login error', err); showError('loginPasswordError','Server error'); if(window.notify) window.notify.error('Server error'); });
    }).catch(err => {
      console.error('Supabase auth error', err);
      // Fallback to legacy backend
      fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})})
        .then(r=>r.json()).then(resp=>{ if(resp && resp.success){ if(resp.token) localStorage.setItem('hub_access_token', resp.token); if(resp.refresh_token) localStorage.setItem('hub_refresh_token', resp.refresh_token); if(window.notify) window.notify.success('Login successful! Welcome back.'); document.getElementById('loginForm').reset(); window.location.href='/index.html'; } else { showError('loginPasswordError','Login failed'); } })
        .catch(e=>{ console.error('fallback error',e); showError('loginPasswordError','Server error'); });
    });
  }
}
function handleCustomerRegistration(ev){ ev.preventDefault(); ['custFirstNameError','custLastNameError','custEmailError','custPasswordError','custConfirmPasswordError'].forEach(clearError); const firstName=document.getElementById('custFirstName').value.trim(); const lastName=document.getElementById('custLastName').value.trim(); const email=document.getElementById('custEmail').value.trim(); const password=document.getElementById('custPassword').value; const confirm=document.getElementById('custConfirmPassword').value; let ok=true; if(!firstName){ showError('custFirstNameError','First name is required'); ok=false;} if(!lastName){ showError('custLastNameError','Last name is required'); ok=false;} if(!validateEmail(email)){ showError('custEmailError','Please enter a valid email'); ok=false;} if(!validatePassword(password)){ showError('custPasswordError','Password must be at least 6 characters'); ok=false;} if(password!==confirm){ showError('custConfirmPasswordError','Passwords do not match'); ok=false;} if(ok){ const data={firstName,lastName,email}; console.log('Customer Registration (pending):',data); pendingRegistrations.customer={...data}; sendOTP(email,'customer'); switchCustomerStep(4); } }
function handleCustomerRegistration(ev){ ev.preventDefault(); ['custFirstNameError','custLastNameError','custEmailError','custPasswordError','custConfirmPasswordError'].forEach(clearError); const firstName=document.getElementById('custFirstName').value.trim(); const lastName=document.getElementById('custLastName').value.trim(); const email=document.getElementById('custEmail').value.trim(); const password=document.getElementById('custPassword').value; const confirm=document.getElementById('custConfirmPassword').value; let ok=true; if(!firstName){ showError('custFirstNameError','First name is required'); ok=false;} if(!lastName){ showError('custLastNameError','Last name is required'); ok=false;} if(!validateEmail(email)){ showError('custEmailError','Please enter a valid email'); ok=false;} if(!validatePassword(password)){ showError('custPasswordError','Password must be at least 6 characters'); ok=false;} if(password!==confirm){ showError('custConfirmPasswordError','Passwords do not match'); ok=false;} if(ok){ const payload={ email, password, role:'customer', first_name:firstName, last_name:lastName };
    fetch('/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
      .then(r=>r.json()).then(resp=>{
        if(resp && resp.success){
          if(resp.token) localStorage.setItem('hub_access_token', resp.token);
          if(resp.refresh_token) localStorage.setItem('hub_refresh_token', resp.refresh_token);
          pendingRegistrations.customer={firstName,lastName,email}; sendOTP(email,'customer'); switchCustomerStep(4);
        } else { showError('custEmailError', resp.error || 'Registration failed'); }
      }).catch(err=>{ console.error(err); showError('custEmailError','Server error'); });
  }
}
function handleSellerStep1(ev){ ev.preventDefault(); ['selFirstNameError','selLastNameError'].forEach(clearError); const first=document.getElementById('selFirstName').value.trim(); const last=document.getElementById('selLastName').value.trim(); let ok=true; if(!first){ showError('selFirstNameError','First name is required'); ok=false;} if(!last){ showError('selLastNameError','Last name is required'); ok=false;} if(ok) switchSellerStep(2); }
function handleSellerStep2(ev){ ev.preventDefault(); ['selBusinessNameError','selBusinessDocError','selBusinessCategoryError','selRegionError','selProvinceError','selCityError'].forEach(clearError); const business=document.getElementById('selBusinessName').value.trim(); const doc=document.getElementById('selBusinessDoc').value; const cat=document.getElementById('selBusinessCategory').value; const region=document.getElementById('selRegion').value; const province=document.getElementById('selProvince').value; const city=document.getElementById('selCity').value; let ok=true; if(!business){ showError('selBusinessNameError','Business name is required'); ok=false;} if(!doc){ showError('selBusinessDocError','Business document is required'); ok=false;} if(!cat){ showError('selBusinessCategoryError','Please select a business category'); ok=false;} if(!region){ showError('selRegionError','Please select a region'); ok=false;} if(!province){ showError('selProvinceError','Please select a province'); ok=false;} if(!city){ showError('selCityError','Please select a city'); ok=false;} if(ok) switchSellerStep(3); }
function handleSellerRegistration(ev){ ev.preventDefault(); ['selEmailError','selPasswordError','selConfirmPasswordError'].forEach(clearError); const first=document.getElementById('selFirstName').value.trim(); const email=document.getElementById('selEmail').value.trim(); const password=document.getElementById('selPassword').value; const confirm=document.getElementById('selConfirmPassword').value; let ok=true; if(!validateEmail(email)){ showError('selEmailError','Please enter a valid email'); ok=false;} if(!validatePassword(password)){ showError('selPasswordError','Password must be at least 6 characters'); ok=false;} if(password!==confirm){ showError('selConfirmPasswordError','Passwords do not match'); ok=false;} if(ok){ const data={ firstName:first, businessName:document.getElementById('selBusinessName').value, category:document.getElementById('selBusinessCategory').value, email }; console.log('Seller Registration (pending):',data); pendingRegistrations.seller={...data}; sendOTP(email,'seller'); switchSellerStep(4); } }
function handleSellerRegistration(ev){ ev.preventDefault(); ['selEmailError','selPasswordError','selConfirmPasswordError'].forEach(clearError); const first=document.getElementById('selFirstName').value.trim(); const email=document.getElementById('selEmail').value.trim(); const password=document.getElementById('selPassword').value; const confirm=document.getElementById('selConfirmPassword').value; let ok=true; if(!validateEmail(email)){ showError('selEmailError','Please enter a valid email'); ok=false;} if(!validatePassword(password)){ showError('selPasswordError','Password must be at least 6 characters'); ok=false;} if(password!==confirm){ showError('selConfirmPasswordError','Passwords do not match'); ok=false;} if(ok){ const payload={ email, password, role:'seller', first_name:first, business_name:document.getElementById('selBusinessName').value, category:document.getElementById('selBusinessCategory').value };
    fetch('/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
      .then(r=>r.json()).then(resp=>{
        if(resp && resp.success){
          if(resp.token) localStorage.setItem('hub_access_token', resp.token);
          if(resp.refresh_token) localStorage.setItem('hub_refresh_token', resp.refresh_token);
          pendingRegistrations.seller={...payload}; sendOTP(email,'seller'); switchSellerStep(4);
        } else { showError('selEmailError', resp.error || 'Registration failed'); }
      }).catch(err=>{ console.error(err); showError('selEmailError','Server error'); });
  }
}
function handleRiderStep1(ev){ ev.preventDefault(); ['ridFirstNameError','ridLastNameError'].forEach(clearError); const first=document.getElementById('ridFirstName').value.trim(); const last=document.getElementById('ridLastName').value.trim(); let ok=true; if(!first){ showError('ridFirstNameError','First name is required'); ok=false;} if(!last){ showError('ridLastNameError','Last name is required'); ok=false;} if(ok) switchRiderStep(2); }
function handleRiderStep2(ev){ ev.preventDefault(); ['ridVehicleTypeError','ridDriverLicenseError','ridPlateNumberError'].forEach(clearError); const vehicle=document.getElementById('ridVehicleType').value; const license=document.getElementById('ridDriverLicense').value; const plate=document.getElementById('ridPlateNumber').value.trim(); let ok=true; if(!vehicle){ showError('ridVehicleTypeError','Please select a vehicle type'); ok=false;} if(!license){ showError('ridDriverLicenseError','Driver license is required'); ok=false;} if(!plate){ showError('ridPlateNumberError','Plate number is required'); ok=false;} if(ok) switchRiderStep(3); }
function handleRiderRegistration(ev){ ev.preventDefault(); ['ridEmailError','ridPasswordError','ridConfirmPasswordError'].forEach(clearError); const first=document.getElementById('ridFirstName').value.trim(); const email=document.getElementById('ridEmail').value.trim(); const password=document.getElementById('ridPassword').value; const confirm=document.getElementById('ridConfirmPassword').value; let ok=true; if(!validateEmail(email)){ showError('ridEmailError','Please enter a valid email'); ok=false;} if(!validatePassword(password)){ showError('ridPasswordError','Password must be at least 6 characters'); ok=false;} if(password!==confirm){ showError('ridConfirmPasswordError','Passwords do not match'); ok=false;} if(ok){ const data={ firstName:first, vehicleType:document.getElementById('ridVehicleType').value, email }; console.log('Rider Registration (pending):',data); pendingRegistrations.rider={...data}; sendOTP(email,'rider'); switchRiderStep(4); } }
function handleRiderRegistration(ev){ ev.preventDefault(); ['ridEmailError','ridPasswordError','ridConfirmPasswordError'].forEach(clearError); const first=document.getElementById('ridFirstName').value.trim(); const email=document.getElementById('ridEmail').value.trim(); const password=document.getElementById('ridPassword').value; const confirm=document.getElementById('ridConfirmPassword').value; let ok=true; if(!validateEmail(email)){ showError('ridEmailError','Please enter a valid email'); ok=false;} if(!validatePassword(password)){ showError('ridPasswordError','Password must be at least 6 characters'); ok=false;} if(password!==confirm){ showError('ridConfirmPasswordError','Passwords do not match'); ok=false;} if(ok){ const payload={ email, password, role:'rider', first_name:first, vehicle_type:document.getElementById('ridVehicleType').value, driver_license:document.getElementById('ridDriverLicense').value };
    fetch('/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
      .then(r=>r.json()).then(resp=>{
        if(resp && resp.success){
          if(resp.token) localStorage.setItem('hub_access_token', resp.token);
          if(resp.refresh_token) localStorage.setItem('hub_refresh_token', resp.refresh_token);
          pendingRegistrations.rider={...payload}; sendOTP(email,'rider'); switchRiderStep(4);
        } else { showError('ridEmailError', resp.error || 'Registration failed'); }
      }).catch(err=>{ console.error(err); showError('ridEmailError','Server error'); });
  }
}
function handleCustomerOTP(ev){ ev.preventDefault(); clearError('custOTPError'); const code=document.getElementById('custOTP').value.trim(); const email = pendingRegistrations.customer?.email || document.getElementById('custEmail')?.value; if(!email){ showError('custOTPError','Missing email'); return;} if(code.length<4){ showError('custOTPError','Enter the verification code'); return;} fetch('/api/auth/verify-otp',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ email: email, code: code }) }).then(r=>r.json()).then(j=>{ if(j && j.success){ showSuccess('customerSuccess',`Account verified for ${pendingRegistrations.customer?.firstName||''}`); pendingRegistrations.customer=null; document.getElementById('customerForm')?.reset(); document.getElementById('customerFormOTP')?.reset?.(); setTimeout(()=>switchForm('login'),1500); } else { showError('custOTPError', j && j.error ? j.error : 'Verification failed'); } }).catch(err=>{ console.error('verify-otp error',err); showError('custOTPError','Server error'); }); }
function handleSellerOTP(ev){ ev.preventDefault(); clearError('sellerOTPError'); const code=document.getElementById('sellerOTP').value.trim(); const email = pendingRegistrations.seller?.email || document.getElementById('selEmail')?.value; if(!email){ showError('sellerOTPError','Missing email'); return;} if(code.length<4){ showError('sellerOTPError','Enter the verification code'); return;} fetch('/api/auth/verify-otp',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ email: email, code: code }) }).then(r=>r.json()).then(j=>{ if(j && j.success){ showSuccess('sellerSuccess','Seller account verified.'); pendingRegistrations.seller=null; ['sellerForm1','sellerForm2','sellerForm3'].forEach(id=>document.getElementById(id).reset?.()); setTimeout(()=>switchForm('login'),1500); } else { showError('sellerOTPError', j && j.error ? j.error : 'Verification failed'); } }).catch(err=>{ console.error('verify-otp error',err); showError('sellerOTPError','Server error'); }); }
function handleRiderOTP(ev){ ev.preventDefault(); clearError('riderOTPError'); const code=document.getElementById('riderOTP').value.trim(); const email = pendingRegistrations.rider?.email || document.getElementById('ridEmail')?.value; if(!email){ showError('riderOTPError','Missing email'); return;} if(code.length<4){ showError('riderOTPError','Enter the verification code'); return;} fetch('/api/auth/verify-otp',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ email: email, code: code }) }).then(r=>r.json()).then(j=>{ if(j && j.success){ showSuccess('riderSuccess','Rider account verified.'); pendingRegistrations.rider=null; ['riderForm1','riderForm2','riderForm3'].forEach(id=>document.getElementById(id).reset?.()); setTimeout(()=>switchForm('login'),1500); } else { showError('riderOTPError', j && j.error ? j.error : 'Verification failed'); } }).catch(err=>{ console.error('verify-otp error',err); showError('riderOTPError','Server error'); }); }

// Initialize auth only when on auth page
window.addEventListener('DOMContentLoaded',()=>{ if(document.body.classList.contains('auth')){ switchForm('login'); } });

// --- Auth helpers: token storage and authFetch wrapper ---
function setAuthTokens(access, refresh){ if(access) localStorage.setItem('hub_access_token', access); if(refresh) localStorage.setItem('hub_refresh_token', refresh); }
function clearAuthTokens(){ localStorage.removeItem('hub_access_token'); localStorage.removeItem('hub_refresh_token'); }

async function authFetch(input, init){
  init = init || {};
  init.headers = init.headers || {};
  const token = localStorage.getItem('hub_access_token');
  if(token) init.headers['Authorization'] = 'Bearer ' + token;
  // Only set Content-Type to JSON if body is not FormData (FormData needs browser to set multipart boundary)
  if(init.body && !(init.body instanceof FormData) && !init.headers['Content-Type']) init.headers['Content-Type'] = 'application/json';
  let res = await fetch(input, init);
  if(res.status === 401){
    const refresh = localStorage.getItem('hub_refresh_token');
    if(!refresh) return res;
    try{
      const r = await fetch('/api/auth/refresh', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ refresh_token: refresh }) });
      if(r.ok){ const j = await r.json(); setAuthTokens(j.token, j.refresh_token); init.headers['Authorization'] = 'Bearer ' + j.token; return fetch(input, init); } else { clearAuthTokens(); return res; }
    }catch(e){ console.error('refresh failed', e); return res; }
  }
  return res;
}

// Messenger Functions for seller.html
function openMessenger() {
    console.log('openMessenger called');
    
    // Set default customer name if not exists
    if (!localStorage.getItem('customer_name')) {
        localStorage.setItem('customer_name', 'Customer');
    }

    // Get panel elements
    const panel = document.getElementById('messagesPanel');
    const messagesList = document.getElementById('messagesList');
    const messagesSearchBar = document.getElementById('messagesSearchBar');
    const chatView = document.getElementById('chatView');
    const backBtn = document.querySelector('.back-to-list');
    const titleEl = document.getElementById('messagesPanelTitle');
    
    console.log('Panel found:', !!panel);
    console.log('Chat view found:', !!chatView);
    
    if (!panel || !chatView) {
        alert('Error: Messages panel not found. Please refresh the page.');
        return;
    }
    
    // Show panel - remove hidden attribute
    panel.removeAttribute('hidden');
    panel.style.display = 'flex';
    
    // Set current chat seller
    window.currentChatSeller = 'groceryshop';
    
    // Hide list, show chat
    if (messagesList) messagesList.style.display = 'none';
    if (messagesSearchBar) messagesSearchBar.style.display = 'none';
    chatView.style.display = 'flex';
    if (backBtn) backBtn.style.display = 'block';
    if (titleEl) titleEl.textContent = 'groceryshop';
    
    // Load messages
    loadChatMessagesForSeller('groceryshop');
    
    // Focus input after short delay
    setTimeout(() => {
        const chatInput = document.getElementById('chatInput');
        if (chatInput) chatInput.focus();
    }, 200);
}

function toggleMessagesPanel() {
    const panel = document.getElementById('messagesPanel');
    const btn = document.querySelector('.messages-btn');
    
    if (panel.hidden) {
        panel.hidden = false;
        btn.setAttribute('aria-expanded', 'true');
    } else {
        panel.hidden = true;
        btn.setAttribute('aria-expanded', 'false');
    }
}

// Open messages panel and focus on a seller chat view
function openSellerChat(sellerName){
    const panel = document.getElementById('messagesPanel');
    const btn = document.querySelector('.messages-btn');
    if (panel.hidden){
        panel.hidden = false;
        if (btn) btn.setAttribute('aria-expanded','true');
    }
    // Switch to chat view
    const list = document.getElementById('messagesList');
    const searchBar = document.getElementById('messagesSearchBar');
    const chatView = document.getElementById('chatView');
    const title = document.getElementById('messagesPanelTitle');
    const backBtn = document.querySelector('.back-to-list');

    if (list) list.style.display = 'none';
    if (searchBar) searchBar.style.display = 'none';
    if (chatView) chatView.style.display = 'flex';
    if (backBtn) backBtn.style.display = 'inline-flex';
    if (title) title.textContent = sellerName || 'Conversation';

    // Seed chat with a welcome if empty
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages && chatMessages.children.length === 0){
        const welcome = document.createElement('div');
        welcome.style.cssText = 'margin:10px 0; text-align:center; color:#7f8c8d; font-size:13px;';
        welcome.textContent = `You are now chatting with ${sellerName || 'seller'}.`;
        chatMessages.appendChild(welcome);
    }
}

function closeMessagesPanel() {
    const panel = document.getElementById('messagesPanel');
    const btn = document.querySelector('.messages-btn');
    panel.hidden = true;
    btn.setAttribute('aria-expanded', 'false');
}

function backToConversationsList() {
    document.getElementById('messagesList').style.display = 'block';
    document.getElementById('messagesSearchBar').style.display = 'block';
    document.getElementById('chatView').style.display = 'none';
    document.querySelector('.back-to-list').style.display = 'none';
    document.getElementById('messagesPanelTitle').textContent = 'Messages';
}

function filterMessageConversations() {
    const searchTerm = document.getElementById('messagesSearch').value.toLowerCase();
    const items = document.querySelectorAll('.message-item');
    
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(searchTerm) ? 'flex' : 'none';
    });
}

function sendMessageInPanel() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message || !window.currentChatSeller) return;
    
    const customerName = localStorage.getItem('customer_name') || 'Customer';
    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    const timestamp = Date.now();
    
    // Get existing messages
    const messages = JSON.parse(localStorage.getItem(`customer_chat_${window.currentChatSeller}`) || '[]');
    
    // Add new message
    messages.push({
        sender: customerName,
        text: message,
        time: time,
        timestamp: timestamp,
        read: true
    });
    
    // Save to localStorage
    localStorage.setItem(`customer_chat_${window.currentChatSeller}`, JSON.stringify(messages));
    
    // Also update seller_messages
    const sellerMessages = JSON.parse(localStorage.getItem('seller_messages') || '[]');
    const existingConversation = sellerMessages.find(m => m.customerName === customerName);
    
    if (existingConversation) {
        existingConversation.lastMessage = message;
        existingConversation.timestamp = new Date().toISOString();
        existingConversation.unread = true;
    } else {
        sellerMessages.push({
            customerId: Date.now(),
            customerName: customerName,
            lastMessage: message,
            timestamp: new Date().toISOString(),
            unread: true
        });
    }
    localStorage.setItem('seller_messages', JSON.stringify(sellerMessages));
    
    // Clear input
    input.value = '';
    
    // Reload chat messages
    loadChatMessagesForSeller(window.currentChatSeller);
}

function loadChatMessagesForSeller(sellerName) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const messages = JSON.parse(localStorage.getItem(`customer_chat_${sellerName}`) || '[]');
    const customerName = localStorage.getItem('customer_name') || 'Customer';
    
    if (messages.length === 0) {
        chatMessages.innerHTML = `
            <div style="text-align: center; padding: 40px 20px;">
                <div style="width: 60px; height: 60px; margin: 0 auto 16px; border-radius: 50%; background: linear-gradient(135deg, #3498db, #2980b9); display: flex; align-items: center; justify-content: center; color: white; font-size: 24px;">
                    <i class="fa fa-store"></i>
                </div>
                <h4 style="margin: 0 0 8px 0; color: #2c3e50;">Start conversation with ${sellerName}</h4>
                <p style="margin: 0; color: #999; font-size: 14px;">Send a message to begin chatting</p>
            </div>
        `;
        return;
    }
    
    chatMessages.innerHTML = messages.map(msg => {
        const isCustomer = msg.sender === 'customer' || msg.sender === customerName;
        const alignment = isCustomer ? 'flex-end' : 'flex-start';
        const bgColor = isCustomer ? '#3498db' : '#ecf0f1';
        const textColor = isCustomer ? 'white' : '#2c3e50';
        
        return `
            <div style="display: flex; justify-content: ${alignment}; margin-bottom: 12px;">
                <div style="max-width: 70%; padding: 10px 14px; border-radius: 18px; background: ${bgColor}; color: ${textColor};">
                    <div style="word-wrap: break-word;">${msg.text}</div>
                    <div style="font-size: 0.7rem; margin-top: 4px; opacity: 0.7;">${msg.time || ''}</div>
                </div>
            </div>
        `;
    }).join('');
    
    // Scroll to bottom
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 100);
    
    // Mark messages as read
    messages.forEach(m => m.read = true);
    localStorage.setItem(`customer_chat_${sellerName}`, JSON.stringify(messages));
}

// Customer Chat Modal functions
function openCustomerChat() {
    const modal = document.getElementById('customerChatModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function insertQuickMessage(text) {
    const input = document.getElementById('customerMessageInput');
    if (input) {
        input.value = text;
        input.focus();
    }
}

function sendCustomerMessage() {
    const input = document.getElementById('customerMessageInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    const chatMessages = document.getElementById('customerChatMessages');
    const messageTime = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    
    const messageHTML = `
        <div style="display: flex; gap: 12px; max-width: 70%; align-self: flex-end; flex-direction: row-reverse;">
            <div style="display: flex; flex-direction: column; gap: 4px; align-items: flex-end;">
                <div style="background: #3498db; color: white; padding: 12px 16px; border-radius: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.08);">
                    <p style="margin: 0; font-size: 14px; line-height: 1.5;">${escapeHtml(message)}</p>
                </div>
                <span style="font-size: 11px; color: #999; padding: 0 4px;">${messageTime}</span>
            </div>
        </div>
    `;
    
    chatMessages.insertAdjacentHTML('beforeend', messageHTML);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    input.value = '';
    console.log('Customer message sent:', message);
}

function handleCustomerMessageKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendCustomerMessage();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// -------------------- Password strength meter --------------------
function evaluatePasswordStrength(pw){
  let score=0;
  if(!pw) return {score:0,label:'',level:0};
  const len = pw.length;
  const hasLower = /[a-z]/.test(pw);
  const hasUpper = /[A-Z]/.test(pw);
  const hasDigit = /[0-9]/.test(pw);
  const hasSpecial = /[^A-Za-z0-9]/.test(pw);
  if(len>=8) score++;
  if(hasLower) score++;
  if(hasUpper) score++;
  if(hasDigit || hasSpecial) score++;
  // normalize to 0-4
  const labels=['Very weak','Weak','Fair','Good','Strong'];
  const label = labels[Math.min(score,4)];
  return { score, label, level: Math.min(score,4) };
}

function updatePasswordMeter(meterEl, labelEl, levelInfo){
  if(!meterEl) return;
  const bars = Array.from(meterEl.querySelectorAll('.bar'));
  bars.forEach((b,i)=>{
    b.classList.remove('active','weak','fair','good','strong');
    if(i < levelInfo.level){
      b.classList.add('active');
      const cls = levelInfo.level<=1 ? 'weak' : (levelInfo.level===2 ? 'fair' : (levelInfo.level===3 ? 'good' : 'strong'));
      b.classList.add(cls);
    }
  });
  if(labelEl) labelEl.textContent = levelInfo.label || 'Enter a password';
}

function wirePasswordMeter(passwordSelector, confirmSelector, meterId, labelId, matchId){
  const pw = document.getElementById(passwordSelector);
  const conf = document.getElementById(confirmSelector);
  const meter = document.getElementById(meterId);
  const label = document.getElementById(labelId);
  const match = document.getElementById(matchId);
  if(!pw || !meter) return;
  // popup element (suffixed 'Popup') or parent popup
  const popup = document.getElementById(meterId.replace(/Meter$/,'') + 'Popup') || meter.parentElement;
  function refresh(){
    const val = pw.value || '';
    const info = evaluatePasswordStrength(val);
    updatePasswordMeter(meter,label,info);
    // show match state
    if(match){
      if(!conf || !conf.value) { match.textContent=''; match.className='pwd-match'; }
      else if(conf.value === val){ match.textContent='Passwords match'; match.className='pwd-match ok'; }
      else { match.textContent='Passwords do not match'; match.className='pwd-match bad'; }
    }
  }
  pw.addEventListener('input', refresh);
  if(conf) conf.addEventListener('input', refresh);
  // show popup on focus, hide on blur when empty
  function showPopup(){ if(popup){ popup.style.display='block'; popup.setAttribute('aria-hidden','false'); } }
  function hidePopupIfEmpty(){ if(popup && !pw.value){ popup.style.display='none'; popup.setAttribute('aria-hidden','true'); } }
  pw.addEventListener('focus', showPopup);
  pw.addEventListener('blur', hidePopupIfEmpty);
  if(conf){ conf.addEventListener('focus', showPopup); conf.addEventListener('blur', hidePopupIfEmpty); }
  // initial
  refresh();
}

document.addEventListener('DOMContentLoaded',()=>{
  // customer
  wirePasswordMeter('custPassword','custConfirmPassword','custPasswordMeter','custPasswordLabel','custPasswordMatch');
  // seller
  wirePasswordMeter('selPassword','selConfirmPassword','selPasswordMeter','selPasswordLabel','selPasswordMatch');
  // rider
  wirePasswordMeter('ridPassword','ridConfirmPassword','ridPasswordMeter','ridPasswordLabel','ridPasswordMatch');
  // wire show/hide toggles
  wirePasswordToggles();
});

function wirePasswordToggles(){
  document.querySelectorAll('.pwd-toggle').forEach(btn=>{
    const target = btn.getAttribute('data-target');
    const input = document.getElementById(target);
    if(!input) return;
    function update(){
      const isPwd = input.type === 'password';
      // toggle aria and class; SVG visibility handled by CSS
      btn.setAttribute('aria-pressed', (!isPwd).toString());
      btn.setAttribute('aria-label', isPwd ? 'Show password' : 'Hide password');
      btn.classList.toggle('showing', !isPwd);
    }
    btn.addEventListener('click', ()=>{
      input.type = input.type === 'password' ? 'text' : 'password';
      input.focus();
      update();
    });
    // keep icon in sync if input type changes elsewhere
    input.addEventListener('input', update);
    update();
  });
}

// Compatibility wrapper: map any legacy `switchCustomerStep(4)` calls to step 2
(function(){
  // override global to ensure 2-step customer flow regardless of earlier duplicates
  window.switchCustomerStep = function(step){
    if(step===4) step = 2;
    ['customerForm','customerFormOTP'].forEach(id=>document.getElementById(id)?.classList.remove('active-step'));
    ['customerStep1','customerStep2'].forEach(id=>document.getElementById(id)?.classList.remove('active'));
    if(step===1){
      document.getElementById('customerForm')?.classList.add('active-step');
      document.getElementById('customerStep1')?.classList.add('active');
    } else if(step===2){
      document.getElementById('customerFormOTP')?.classList.add('active-step');
      document.getElementById('customerStep2')?.classList.add('active');
    }
  };
})();

// Account button authentication check - intercept clicks to account.html
(function() {
  'use strict';
  
  /**
   * Check if user is authenticated before allowing access to account page
   */
  function checkAuthBeforeAccountAccess(event) {
    const token = localStorage.getItem('hub_access_token');
    
    if (!token) {
      // No token - prevent navigation and redirect to login
      event.preventDefault();
      event.stopPropagation();
      window.location.href = '/loginregister.html';
      return false;
    }
    
    // Token exists - allow navigation
    return true;
  }
  
  /**
   * Initialize account button protection
   */
  function initAccountButtonProtection() {
    // Add click handlers to all account links
    document.addEventListener('click', function(event) {
      const target = event.target.closest('a[href="account.html"], a[href="/account.html"], a[href*="account.html"]');
      
      if (target) {
        checkAuthBeforeAccountAccess(event);
      }
    }, true); // Use capture phase to intercept before other handlers
  }
  
  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAccountButtonProtection);
  } else {
    initAccountButtonProtection();
  }
  
})();
