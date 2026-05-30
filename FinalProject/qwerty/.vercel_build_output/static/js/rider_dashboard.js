// =====================================================================
// RIDER DASHBOARD - Main JavaScript File
// Features: Delivery Management, Live Tracking, Earnings, Statistics
// =====================================================================

// Global Variables
let riderData = {};
let deliveries = [];
let currentDelivery = null;

// Map variables
let map = null;
let userMarker = null;
let pickupMarker = null;
let deliveryMarker = null;
let routePath = null;

// =====================================================================
// HELPER FUNCTIONS
// =====================================================================

/**
 * Format customer address - handles both plain text and JSON format
 * @param {string} address - Address string (may contain ||| separator with JSON)
 * @returns {string} - Formatted address string
 */
function formatAddress(address) {
    if (!address) return 'N/A';
    
    // Check if address contains JSON data (separated by |||)
    if (address.includes('|||')) {
        const parts = address.split('|||');
        const plainAddress = parts[0] ? parts[0].trim() : '';
        
        if (parts.length > 1 && parts[1]) {
            try {
                const addressData = JSON.parse(parts[1]);
                // Prefer full_address from JSON
                if (addressData.full_address) {
                    return addressData.full_address;
                }
                // Build address from components
                if (addressData.address_line1) {
                    const addressParts = [addressData.address_line1];
                    if (addressData.address_line2) addressParts.push(addressData.address_line2);
                    if (addressData.city) addressParts.push(addressData.city);
                    if (addressData.province) addressParts.push(addressData.province);
                    if (addressData.postal_code) addressParts.push(addressData.postal_code);
                    return addressParts.join(', ');
                }
            } catch (e) {
                console.warn('Failed to parse address JSON:', e);
            }
        }
        
        // If JSON parsing fails or no JSON, use the plain address part
        return plainAddress || 'N/A';
    }
    
    // Return plain address if no JSON format
    return address.trim();
}

/**
 * Update rider service fee display in HTML
 */
function updateRiderFeeDisplay() {
    const feePercentage = window.riderServiceFeePercentage || 2.5;
    
    const productSalesHeading = document.getElementById('productSalesHeading');
    if (productSalesHeading) {
        productSalesHeading.textContent = 'Total Product Sales';
    }

    const platformFeeHeading = document.getElementById('platformFeeHeading');
    if (platformFeeHeading) {
        platformFeeHeading.textContent = `Delivery Fee (${feePercentage}%)`;
    }
    
    const feeHeader = document.getElementById('feeHeader');
    if (feeHeader) {
        feeHeader.textContent = `Delivery Fee (${feePercentage}%)`;
    }
}

// =====================================================================
// DATA LOADING
// =====================================================================

async function loadRiderDashboard() {
    try {
        const response = await authFetch('/api/rider/dashboard');
        if (!response.ok) {
            console.warn('Dashboard API unavailable, using defaults');
            return;
        }
        
        const data = await response.json();
        if (data.success) {
            const dash = data.dashboard;
            riderData = dash.rider_info || {};
            
            // Store dashboard data globally for use in statistics
            window.lastDashboardData = dash;
            
            // Helper function to safely set text content
            function safeSetText(elementId, value) {
                const element = document.getElementById(elementId);
                if (element) {
                    element.textContent = value;
                }
            }
            
            // Set profile name
            safeSetText('profileName', `${riderData.first_name || ''} ${riderData.last_name || ''}`.trim() || 'Rider');
            
            // Update sidebar avatar with profile picture
            const avatarUrl = riderData.avatar_url;
            console.log('Dashboard - Rider avatar URL:', avatarUrl);
            const profileAvatarEl = document.getElementById('profileAvatar');
            if (profileAvatarEl) {
                if (avatarUrl) {
                    console.log('Dashboard - Updating sidebar avatar with:', avatarUrl);
                    profileAvatarEl.style.backgroundImage = `url(${avatarUrl})`;
                    profileAvatarEl.style.backgroundSize = 'cover';
                    profileAvatarEl.style.backgroundPosition = 'center';
                    profileAvatarEl.textContent = '';
                } else {
                    profileAvatarEl.style.backgroundImage = '';
                    profileAvatarEl.textContent = '👤';
                }
            }
            
            // Set active deliveries
            safeSetText('activeDeliveries', dash.active_deliveries || 0);
            
            // Set completed deliveries today
            safeSetText('completedToday', dash.completed_today || 0);
            
            // Set total earnings
            const totalEarnings = dash.total_earnings || 0;
            safeSetText('totalEarnings', '₱' + totalEarnings.toLocaleString('en-PH', { minimumFractionDigits: 2 }));
            
            // Set earnings today
            const earningsToday = dash.earnings_today || 0;
            safeSetText('earningsToday', '₱' + earningsToday.toLocaleString('en-PH', { minimumFractionDigits: 2 }));
            
            // Store rider delivery fee rate from dashboard (2.5% of product sales)
            window.riderServiceFeeRate = dash.rider_service_fee_rate || 0.025;
            window.riderServiceFeePercentage = dash.rider_service_fee_percentage || 2.5;
            
            // Update platform fee label in HTML
            updateRiderFeeDisplay();
            
            // Set average rating
            const avgRating = dash.average_rating || 0;
            safeSetText('avgRating', avgRating.toFixed(1));
            
            // Set next delivery info
            if (dash.next_delivery) {
                const next = dash.next_delivery;
                const nextDeliveryEl = document.getElementById('nextDeliveryInfo');
                if (nextDeliveryEl) {
                    nextDeliveryEl.innerHTML = `
                        <strong>Order ID:</strong> #${next.id || 'N/A'}<br>
                        <strong>Customer:</strong> ${next.customer_name || 'N/A'}<br>
                        <strong>Address:</strong> ${formatAddress(next.customer_address) || 'N/A'}<br>
                        <strong>Status:</strong> <span class="delivery-status status-${(next.status || 'pending').toLowerCase()}">${formatStatus(next.status || 'pending')}</span>
                    `;
                }
            } else {
                const nextDeliveryEl = document.getElementById('nextDeliveryInfo');
                if (nextDeliveryEl) {
                    nextDeliveryEl.innerHTML = '<p class="no-data">No active deliveries</p>';
                }
            }
            
            // Update dashboard stats with delivery data
            updateDashboardStats();
        }
    } catch (err) {
        console.error('Dashboard error:', err);
    }
}

// Global variable to track available orders count
let availableOrdersCount = 0;
let hasShownInitialNotification = false;
let _ordersLoading = false;
let _lastOrdersRefresh = 0;

async function refreshRiderData(options = {}) {
    const { dashboard = true, orders = true, force = false } = options;
    const now = Date.now();
    if (!force && now - _lastOrdersRefresh < 1500) return;
    _lastOrdersRefresh = now;

    if (dashboard) {
        try {
            await loadRiderDashboard();
        } catch (err) {
            console.warn('Dashboard refresh failed:', err);
        }
    }
    if (orders) {
        await loadRiderOrders({ silent: true });
    }
}

async function loadRiderOrders(options = {}) {
    const { silent = false } = options;
    if (_ordersLoading) return;
    _ordersLoading = true;
    try {
        let assignedOrders = [];
        const assignedResponse = await authFetch('/api/rider/orders');
        if (assignedResponse.ok) {
            const assignedData = await assignedResponse.json();
            assignedOrders = assignedData.success ? (assignedData.orders || []) : [];
        } else {
            console.warn('Assigned orders API unavailable');
        }
        
        let availableOrders = [];
        const availableResponse = await authFetch('/api/riders/available-orders');
        if (availableResponse.ok) {
            const availableData = await availableResponse.json();
            availableOrders = availableData.success ? (availableData.data || []) : [];
        } else {
            console.warn('Available orders API unavailable');
        }
        
        // Update available orders count
        const previousCount = availableOrdersCount;
        availableOrdersCount = availableOrders.length;
        
        // Combine and format orders
        deliveries = [
            ...assignedOrders.map(o => ({ ...o, type: 'assigned' })),
            ...availableOrders.map(o => ({ ...o, type: 'available' }))
        ];
        
        // Update badge and show notification
        updateAvailableOrdersBadge(availableOrdersCount);
        
        // Show notification on initial load or when new orders become available
        if (availableOrdersCount > 0) {
            if (!hasShownInitialNotification) {
                // Initial notification on login/dashboard load
                showAvailableOrdersNotification(availableOrdersCount);
                hasShownInitialNotification = true;
            } else if (availableOrdersCount > previousCount && previousCount > 0) {
                // New orders became available
                showAvailableOrdersNotification(availableOrdersCount - previousCount, true);
            }
        }
        
            renderDeliveriesTable();
        loadDeliveries();
        
        // Update dashboard stats after loading orders
        updateDashboardStats();
        
        // Update statistics if stats section is active
        const statsSection = document.getElementById('statsSection');
        if (statsSection && statsSection.classList.contains('active')) {
            loadStatistics();
        }
    } catch (err) {
        console.error('Orders error:', err);
        if (!silent) {
            showNotification('Failed to load orders. Please refresh the page.', 'error');
        }
    } finally {
        _ordersLoading = false;
    }
}

function updateAvailableOrdersBadge(count) {
    // Update badge on "Available" filter button
    const availableBtn = document.querySelector('.filter-btn[data-filter="available"]');
    if (availableBtn) {
        // Remove existing badge
        const existingBadge = availableBtn.querySelector('.order-badge');
        if (existingBadge) {
            existingBadge.remove();
        }
        
        // Add badge if there are available orders
        if (count > 0) {
            const badge = document.createElement('span');
            badge.className = 'order-badge';
            badge.textContent = count;
            badge.style.cssText = `
                display: inline-block;
                background: #ef4444;
                color: white;
                border-radius: 12px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 700;
                margin-left: 8px;
                min-width: 20px;
                text-align: center;
                animation: pulse 2s infinite;
            `;
            availableBtn.appendChild(badge);
        }
    }
    
    // Update badge on sidebar "Deliveries" menu item
    const deliveriesNavLink = document.querySelector('.nav-link[data-label="Active Deliveries"]');
    if (deliveriesNavLink) {
        // Remove existing badge
        const existingNavBadge = deliveriesNavLink.querySelector('.nav-badge');
        if (existingNavBadge) {
            existingNavBadge.remove();
        }
        
        // Add badge if there are available orders
        if (count > 0) {
            const navBadge = document.createElement('span');
            navBadge.className = 'nav-badge';
            navBadge.textContent = count;
            navBadge.style.cssText = `
                display: inline-block;
                background: #ef4444;
                color: white;
                border-radius: 10px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: 700;
                margin-left: auto;
                min-width: 18px;
                text-align: center;
                animation: pulse 2s infinite;
            `;
            deliveriesNavLink.appendChild(navBadge);
        }
    }
}

function showAvailableOrdersNotification(count, isNew = false) {
    const message = isNew 
        ? `🎉 ${count} new order${count > 1 ? 's' : ''} available for pickup!`
        : `📦 ${count} order${count > 1 ? 's' : ''} available for pickup!`;
    
    const notificationMessage = `${message} Click "Available" to view and accept.`;
    
    // Use info notification for available orders
    showNotification(notificationMessage, 'info');
}


function renderDeliveriesTable() {
    const tbody = document.getElementById('deliveriesTableBody');
    if (!tbody) return;
    
    if (deliveries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px;">No deliveries found</td></tr>';
        return;
    }
    
    tbody.innerHTML = deliveries.map(d => `
        <tr>
            <td>#${d.id}</td>
            <td>${d.customer_name || 'N/A'}</td>
            <td>${formatAddress(d.customer_address) || 'N/A'}</td>
            <td>₱${(d.rider_earnings ?? d.delivery_fee ?? 0).toLocaleString('en-PH', { minimumFractionDigits: 2 })}</td>
            <td><span class="status-badge ${getStatusClass(d.status)}">${d.status || 'pending'}</span></td>
            <td>${new Date(d.created_at).toLocaleDateString()}</td>
        </tr>
    `).join('');
}

function getStatusClass(status) {
    const statusMap = {
        'placed': 'pending',
        'pending': 'pending',
        'processing': 'pending',
        'ready': 'pending',
        'confirmed': 'pending',
        'dispatched': 'in-progress',
        'in-transit': 'in-progress',
        'delivered': 'completed',
        'completed': 'completed',
        'cancelled': 'cancelled'
    };
    return statusMap[status] || 'pending';
}

function formatStatus(status) {
    const statusMap = {
        'placed': 'Placed',
        'pending': 'Pending',
        'processing': 'Processing',
        'ready': 'Ready for Pickup',
        'dispatched': 'Pick-Up Scheduled',
        'in-transit': 'On the Way',
        'delivered': 'Delivered',
        'completed': 'Completed',
        'cancelled': 'Cancelled'
    };
    return statusMap[status] || status;
}

// =====================================================================
// INITIALIZATION
// =====================================================================

document.addEventListener('DOMContentLoaded', function() {
    refreshRiderData({ force: true });
    console.log('Rider Dashboard Initialized');

    // Webhook-driven updates via Supabase Realtime (replaces polling)
    if (window.hubLiveUpdates) {
        window.hubLiveUpdates.onOrdersChanged(() => {
            refreshRiderData({ dashboard: true, orders: true });
        });
        window.hubLiveUpdates.start().then((ok) => {
            if (ok) console.log('Rider dashboard: live order updates connected');
        });
    }

    loadRiderProfile();
});

function updateDashboardStats() {
    // Helper function to safely set text content
    function safeSetText(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    // Count active deliveries (dispatched, in-transit, ready)
    const active = deliveries.filter(d => 
        d.status === 'dispatched' || 
        d.status === 'in-transit' || 
        d.status === 'ready'
    ).length;
    
    // Count available orders (pending/ready without rider)
    const available = deliveries.filter(d => 
        d.type === 'available' && 
        (d.status === 'ready' || d.status === 'pending')
    ).length;

    // Update active deliveries count
    safeSetText('activeDeliveries', active);
    
    // Update notification count (available orders)
    safeSetText('notificationCount', available);

    // Update next delivery if not already set from API
    const nextDeliveryEl = document.getElementById('nextDeliveryInfo');
    if (nextDeliveryEl && (!nextDeliveryEl.innerHTML || nextDeliveryEl.innerHTML.includes('no-data'))) {
        const nextDelivery = deliveries.find(d => 
            d.status === 'dispatched' || 
            d.status === 'in-transit' || 
            d.status === 'ready'
        );
        
    if (nextDelivery) {
            nextDeliveryEl.innerHTML = `
                <strong>Order ID:</strong> #${nextDelivery.id || 'N/A'}<br>
                <strong>Customer:</strong> ${nextDelivery.customer_name || 'N/A'}<br>
                <strong>Address:</strong> ${formatAddress(nextDelivery.customer_address) || 'N/A'}<br>
                <strong>Status:</strong> <span class="delivery-status status-${(nextDelivery.status || 'pending').toLowerCase()}">${formatStatus(nextDelivery.status || 'pending')}</span>
        `;
        } else {
            nextDeliveryEl.innerHTML = '<p class="no-data">No active deliveries</p>';
        }
    }

    // Service area info (can be customized based on rider data)
    const serviceAreaEl = document.getElementById('serviceAreaInfo');
    if (serviceAreaEl) {
        const serviceArea = riderData.service_area || 'Metro Manila';
        const serviceHours = riderData.service_hours || '8:00 AM - 11:00 PM';
        const availability = riderData.availability || 'online';
        const availabilityColor = availability === 'online' ? '#27AE60' : '#95A5A6';
        const availabilityText = availability === 'online' ? 'Online' : 'Offline';
        
        serviceAreaEl.innerHTML = `
            <strong>Current Area:</strong> ${serviceArea}<br>
            <strong>Service Hours:</strong> ${serviceHours}<br>
            <strong>Active Status:</strong> <span style="color: ${availabilityColor};">● ${availabilityText}</span>
    `;
    }
}

// =====================================================================
// NAVIGATION & SECTION SWITCHING
// =====================================================================

function switchSection(sectionName, ev) {
    // Hide any section containers we know about
    document.querySelectorAll('.content-section, .section').forEach(section => section.classList.remove('active'));

    // Show selected section by id
    const sectionId = sectionName + 'Section';
    const section = document.getElementById(sectionId);
    if (section) section.classList.add('active');

    // Update nav links robustly
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    let activated = false;
    if (ev) {
        const nav = (ev.currentTarget && ev.currentTarget.closest) ? ev.currentTarget.closest('.nav-link') : (ev.target && ev.target.closest ? ev.target.closest('.nav-link') : null);
        if (nav) { nav.classList.add('active'); activated = true; }
    }
    if (!activated) {
        const normalized = (sectionName||'').replace(/\s/g,'').toLowerCase();
        document.querySelectorAll('.nav-link').forEach(link => {
            if (((link.getAttribute('data-label')||'').replace(/\s/g,'').toLowerCase()) === normalized) link.classList.add('active');
        });
    }

    // Update page title
    const titleMap = {
        dashboard: 'Dashboard',
        deliveries: 'Active Deliveries',
        'return-pickups': 'Return Pickups',
        tracking: 'Live Tracking',
        earnings: 'Earnings Report',
        history: 'Delivery History',
        stats: 'Performance Statistics',
        profile: 'Rider Profile'
    };
    document.getElementById('pageTitle').textContent = titleMap[sectionName] || 'Dashboard';

    // Load section-specific data
    if (sectionName === 'dashboard') {
        // Refresh dashboard data when switching to dashboard section
        loadRiderDashboard();
        updateDashboardStats();
    } else if (sectionName === 'deliveries') {
        loadDeliveries();
    } else if (sectionName === 'return-pickups') {
        loadReturnPickups();
        // Poll for new return pickups every 30 seconds
        if (window.returnPickupPollInterval) {
            clearInterval(window.returnPickupPollInterval);
        }
        window.returnPickupPollInterval = setInterval(() => {
            loadReturnPickups();
        }, 30000);
    } else if (sectionName === 'tracking') {
        // Initialize map if not already initialized
        setTimeout(async () => {
            if (!map) {
                initializeMap();
            } else {
                map.invalidateSize();
            }
            // If there's a current delivery, ensure it has coordinates
            if (currentDelivery && (!currentDelivery.pickupCoords || !currentDelivery.deliveryCoords)) {
                await geocodeDeliveryAddresses(currentDelivery);
                updateMapForDelivery(currentDelivery);
            }
        }, 100);
    } else if (sectionName === 'earnings') {
        // Initialize date inputs if not set
        const startDateInput = document.getElementById('earningsStartDate');
        const endDateInput = document.getElementById('earningsEndDate');
        if (startDateInput && !startDateInput.value) {
            const today = new Date();
            const thirtyDaysAgo = new Date(today);
            thirtyDaysAgo.setDate(today.getDate() - 30);
            startDateInput.value = thirtyDaysAgo.toISOString().split('T')[0];
        }
        if (endDateInput && !endDateInput.value) {
            const today = new Date();
            endDateInput.value = today.toISOString().split('T')[0];
        }
        updateEarningsReport();
    } else if (sectionName === 'history') {
        // Don't set default date - allow showing all deliveries
        // User can optionally filter by date
        loadDeliveryHistory();
    } else if (sectionName === 'stats') {
        loadStatistics();
    } else if (sectionName === 'profile') {
        loadRiderProfile();
    }

    // Close sidebar on mobile
    const sidebar = document.querySelector('.rider-sidebar');
    if (window.innerWidth <= 768) {
        sidebar.classList.remove('active');
    }
}

// =====================================================================
// DELIVERIES SECTION
// =====================================================================

function loadDeliveries() {
    const container = document.getElementById('deliveriesContainer');
    if (!container) return;
    
    const filter = document.querySelector('.filter-btn.active')?.dataset.filter || 'all';
    
    let filtered = deliveries;
    if (filter === 'available') {
        filtered = deliveries.filter(d => d.type === 'available');
    } else if (filter === 'assigned') {
        filtered = deliveries.filter(d => d.type === 'assigned');
    } else if (filter !== 'all') {
        filtered = deliveries.filter(d => {
            const status = d.status || 'pending';
            if (filter === 'pending') return status === 'pending' || status === 'placed' || status === 'ready';
            if (filter === 'in-progress') return status === 'dispatched' || status === 'in-transit';
            if (filter === 'completed') return status === 'delivered' || status === 'completed';
            return false;
        });
    }

    if (filtered.length === 0) {
        container.innerHTML = '<p class="no-data">No deliveries found</p>';
        return;
    }

    container.innerHTML = filtered.map(delivery => {
        const items = delivery.items ? (typeof delivery.items === 'string' ? delivery.items.split(',') : delivery.items) : [];
        const itemsText = items.length > 0 ? items.slice(0, 3).join(', ') + (items.length > 3 ? '...' : '') : 'N/A';
        const sellerName = delivery.seller_name || 'Seller';
        const customerName = delivery.customer_name || 'Customer';
        const customerAddress = formatAddress(delivery.customer_address) || 'Address not provided';
        const customerPhone = delivery.customer_phone || 'N/A';
        // Ensure deliveryFee and total are numbers (convert from string if needed)
        const deliveryFee = parseFloat(delivery.delivery_fee) || 0;
        const total = parseFloat(delivery.total) || 0;
        const status = delivery.status || 'pending';
        const orderId = delivery.id;
        const isAvailable = delivery.type === 'available';
        
        return `
        <div class="delivery-card ${status} ${isAvailable ? 'available-order' : ''}" onclick="selectDelivery(${orderId})">
            <div class="delivery-header">
                <h4>Order #${orderId} ${isAvailable ? '<span class="badge-available">Available</span>' : ''}</h4>
                <span class="delivery-status status-${getStatusClass(status)}">${formatStatus(status)}</span>
            </div>
            <div class="delivery-info">
                <p><strong>From:</strong> ${sellerName}</p>
                <p><strong>To:</strong> ${customerAddress}</p>
            </div>
            <div class="delivery-info">
                <p><strong>Customer:</strong> ${customerName}</p>
                <p><strong>Phone:</strong> ${customerPhone}</p>
                <p><strong>Items:</strong> ${itemsText}</p>
            </div>
            <div class="delivery-info">
                <p><strong>Delivery Fee:</strong> ₱${deliveryFee.toFixed(2)}</p>
                <p><strong>Total:</strong> ₱${total.toFixed(2)}</p>
                <p><strong>Date:</strong> ${new Date(delivery.created_at).toLocaleDateString()}</p>
            </div>
            ${isAvailable ? `
            <div class="delivery-actions">
                <button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); acceptOrder(${orderId})">
                    <i class="fas fa-check"></i> Accept Order
                </button>
            </div>
            ` : ''}
        </div>
        `;
    }).join('');
}

function filterDeliveries(status, ev) {
    // Update filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Find and activate the clicked button
    const event = ev || window.event;
    if (event && event.target) {
        const btn = event.target.closest('.filter-btn') || event.target;
        if (btn) {
            btn.classList.add('active');
            btn.dataset.filter = status;
        }
    } else {
        // If no event, find button by data-filter attribute
        const btn = document.querySelector(`.filter-btn[data-filter="${status}"]`);
        if (btn) {
            btn.classList.add('active');
        }
    }

    loadDeliveries();
}

async function selectDelivery(deliveryId) {
    currentDelivery = deliveries.find(d => d.id === deliveryId);
    
    if (!currentDelivery) {
        console.error('Delivery not found:', deliveryId);
        return;
    }
    
    // Geocode addresses if coordinates are missing
    if (!currentDelivery.pickupCoords || !currentDelivery.deliveryCoords) {
        await geocodeDeliveryAddresses(currentDelivery);
    }
    
    // Update tracking map
    if (map && currentDelivery) {
        updateMapForDelivery(currentDelivery);
    }

    // Update sidebar details
    updateDeliveryDetails();

    // Show action buttons based on status
    updateActionButtons();
}

function updateDeliveryDetails() {
    if (!currentDelivery) {
        const detailsEl = document.getElementById('currentDeliveryDetails');
        if (detailsEl) {
            detailsEl.innerHTML = '<p class="no-data">Select a delivery to view details</p>';
        }
        return;
    }

    const items = currentDelivery.items ? (typeof currentDelivery.items === 'string' ? currentDelivery.items.split(',') : currentDelivery.items) : [];
    const itemsText = items.length > 0 ? items.join(', ') : 'N/A';
    const sellerName = currentDelivery.seller_name || 'Seller';
    const customerName = currentDelivery.customer_name || 'Customer';
    const customerPhone = currentDelivery.customer_phone || 'N/A';
        const customerAddress = formatAddress(currentDelivery.customer_address) || 'Address not provided';
    
    // Parse detailed customer information if available (from JSON stored in address)
    let customerDetails = null;
    const rawAddress = currentDelivery.customer_address || '';
    if (rawAddress && rawAddress.includes('|||')) {
        const parts = rawAddress.split('|||');
        if (parts.length > 1) {
            try {
                customerDetails = JSON.parse(parts[1]);
            } catch (e) {
                console.warn('Failed to parse customer details JSON:', e);
            }
        }
    }
    
    const fullAddress = customerAddress;
    const customerEmail = customerDetails ? customerDetails.email : null;
    const addressLine1 = customerDetails ? customerDetails.address_line1 : null;
    const addressLine2 = customerDetails ? customerDetails.address_line2 : null;
    const city = customerDetails ? customerDetails.city : null;
    const province = customerDetails ? customerDetails.province : null;
    const region = customerDetails ? customerDetails.region : null;
    const postalCode = customerDetails ? customerDetails.postal_code : null;
    const deliveryNotes = customerDetails ? customerDetails.notes : null;
    
    // Build address display with all components
    let addressDisplay = fullAddress;
    if (customerDetails && (addressLine1 || city || province)) {
        const addressParts = [];
        if (addressLine1) addressParts.push(addressLine1);
        if (addressLine2) addressParts.push(addressLine2);
        if (city) addressParts.push(city);
        if (province) addressParts.push(province);
        if (region) addressParts.push(region);
        if (postalCode) addressParts.push(`Postal Code: ${postalCode}`);
        if (addressParts.length > 0) {
            addressDisplay = addressParts.join(', ');
        }
    }
    
    // Ensure deliveryFee and total are numbers (convert from string if needed)
    const deliveryFee = parseFloat(currentDelivery.delivery_fee) || 0;
    const total = parseFloat(currentDelivery.total) || 0;
    const status = currentDelivery.status || 'pending';
    const orderDate = currentDelivery.created_at ? new Date(currentDelivery.created_at).toLocaleString() : 'N/A';

    const details = `
        <div class="delivery-detail-item">
            <strong>Order ID:</strong> #${currentDelivery.id}
        </div>
        <div class="delivery-detail-item">
            <strong>Status:</strong> <span class="delivery-status status-${getStatusClass(status)}">${formatStatus(status)}</span>
        </div>
        <div class="delivery-detail-item">
            <strong>Customer Name:</strong> ${customerName}
        </div>
        ${customerEmail ? `<div class="delivery-detail-item"><strong>Email:</strong> <a href="mailto:${customerEmail}">${customerEmail}</a></div>` : ''}
        <div class="delivery-detail-item">
            <strong>Phone:</strong> <a href="tel:${customerPhone}">${customerPhone}</a>
        </div>
        <div class="delivery-detail-item">
            <strong>Pickup From:</strong> ${sellerName}
        </div>
        <div class="delivery-detail-item">
            <strong>Deliver To:</strong><br>
            <div style="margin-top: 8px; padding: 12px; background: #f8f9fa; border-radius: 6px; line-height: 1.6;">
                ${addressDisplay}
            </div>
        </div>
        ${deliveryNotes ? `<div class="delivery-detail-item"><strong>Delivery Notes:</strong> ${deliveryNotes}</div>` : ''}
        <div class="delivery-detail-item">
            <strong>Items:</strong> ${itemsText}
        </div>
        <div class="delivery-detail-item">
            <strong>Delivery Fee:</strong> ₱${deliveryFee.toFixed(2)}
        </div>
        <div class="delivery-detail-item">
            <strong>Total:</strong> ₱${total.toFixed(2)}
        </div>
        <div class="delivery-detail-item">
            <strong>Order Date:</strong> ${orderDate}
        </div>
    `;

    const detailsEl = document.getElementById('currentDeliveryDetails');
    if (detailsEl) {
        detailsEl.innerHTML = details;
    }
}

function updateActionButtons() {
    const acceptBtn = document.getElementById('acceptBtn');
    const startBtn = document.getElementById('startBtn');
    const callBtn = document.getElementById('callBtn');
    const completeBtn = document.getElementById('completeBtn');
    const markCompletedBtn = document.getElementById('markCompletedBtn');

    // Hide all buttons
    [acceptBtn, startBtn, callBtn, completeBtn, markCompletedBtn].forEach(btn => {
        if (btn) btn.style.display = 'none';
    });

    if (!currentDelivery) return;

    const status = currentDelivery.status || 'pending';
    const isAvailable = currentDelivery.type === 'available';

    // Show call button if we have customer phone
    if (currentDelivery.customer_phone && !isAvailable) {
        if (callBtn) callBtn.style.display = 'flex';
    }
    
    // Show accept button for available orders
    if (isAvailable && (status === 'ready' || status === 'placed')) {
        if (acceptBtn) acceptBtn.style.display = 'flex';
    }
    
    // Show "Start Delivery" (mark as in-transit) for dispatched orders
    if (!isAvailable && status === 'dispatched') {
        if (startBtn) startBtn.style.display = 'flex';
    }
    
    // Show "Complete Delivery" (mark as delivered) for in-transit orders
    if (!isAvailable && status === 'in-transit') {
        if (completeBtn) completeBtn.style.display = 'flex';
    }
    
    // Show "Mark as Completed" for delivered orders
    if (!isAvailable && status === 'delivered') {
        if (markCompletedBtn) markCompletedBtn.style.display = 'flex';
    }
}

// =====================================================================
// DELIVERY ACTIONS
// =====================================================================

async function acceptOrder(orderId) {
    try {
        const response = await authFetch('/api/riders/accept-order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ order_id: orderId })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showNotification(`Order #${orderId} accepted successfully!`, 'success');
            // Reload orders
            await loadRiderOrders();
            // Select the accepted order
            selectDelivery(orderId);
        } else {
            throw new Error(data.error || 'Failed to accept order');
        }
    } catch (err) {
        console.error('Accept order error:', err);
        showNotification(err.message || 'Failed to accept order. Please try again.', 'error');
    }
}

function acceptDelivery() {
    if (!currentDelivery) return;
    acceptOrder(currentDelivery.id);
}

async function startDelivery() {
    if (!currentDelivery) return;
    
    try {
        const response = await authFetch(`/api/orders/${currentDelivery.id}/delivery-update`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: 'in-transit',
                notes: 'Picked up from seller, heading to customer'
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showNotification('Order marked as "On the Way"! Navigate to customer location.', 'success');
            await loadRiderOrders();
            selectDelivery(currentDelivery.id);
        } else {
            throw new Error(data.error || 'Failed to update delivery status');
        }
    } catch (err) {
        console.error('Start delivery error:', err);
        showNotification(err.message || 'Failed to update delivery status. Please try again.', 'error');
}
}

async function completeDelivery() {
    if (!currentDelivery) return;

    if (!confirm('Confirm that you have delivered the order to the customer?')) {
        return;
    }
    
    try {
        const response = await authFetch(`/api/orders/${currentDelivery.id}/delivery-update`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: 'delivered',
                notes: 'Order delivered to customer'
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showNotification('Order marked as delivered! You can now mark it as completed after confirming with the customer.', 'success');
            await loadRiderOrders();
            await loadRiderDashboard();
            selectDelivery(currentDelivery.id);
        } else {
            throw new Error(data.error || 'Failed to mark as delivered');
        }
    } catch (err) {
        console.error('Complete delivery error:', err);
        showNotification(err.message || 'Failed to mark as delivered. Please try again.', 'error');
}
}

async function markOrderCompleted() {
    if (!currentDelivery) return;

    if (!confirm('Mark this order as completed? This will finalize the delivery process.')) {
        return;
    }
    
    try {
        const response = await authFetch(`/api/orders/${currentDelivery.id}/delivery-update`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: 'completed',
                notes: 'Order completed and finalized'
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showNotification('Order marked as completed! Thank you for the delivery.', 'success');
            await loadRiderOrders();
            await loadRiderDashboard();
            currentDelivery = null;
    updateDeliveryDetails();
    updateActionButtons();
        } else {
            throw new Error(data.error || 'Failed to mark as completed');
        }
    } catch (err) {
        console.error('Mark completed error:', err);
        showNotification(err.message || 'Failed to mark as completed. Please try again.', 'error');
    }
}

function callCustomer() {
    if (!currentDelivery) return;
    
    const customerName = currentDelivery.customer_name || 'Customer';
    const customerPhone = currentDelivery.customer_phone || '';
    
    if (customerPhone) {
        // Create a tel: link to trigger phone call
        window.location.href = `tel:${customerPhone}`;
        showNotification(`Calling ${customerName}...`, 'info');
    } else {
        showNotification('Customer phone number not available', 'error');
    }
}

// =====================================================================
// LIVE TRACKING & MAP
// =====================================================================

function initializeMap() {
    try {
        // Check if Leaflet is loaded
        if (typeof L === 'undefined') {
            console.error('Leaflet library not loaded');
            const mapElement = document.getElementById('map');
            if (mapElement) {
                mapElement.innerHTML = '<p style="padding: 20px; text-align: center; color: #666;">Map library not loaded. Please refresh the page.</p>';
            }
            return;
        }

        // Check if map element exists
        const mapElement = document.getElementById('map');
        if (!mapElement) {
            console.error('Map element not found');
            return;
        }

        // Don't reinitialize if map already exists
        if (map) {
            map.invalidateSize();
            // Update map with current delivery if one is selected
            if (currentDelivery) {
                updateMapForDelivery(currentDelivery);
            }
            return;
        }

    // Initialize Leaflet map centered on Manila
    map = L.map('map').setView([14.5543, 120.9795], 14);

    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);

    // Add user location marker
    userMarker = L.circleMarker([14.5543, 120.9795], {
        radius: 8,
        fillColor: '#FF6B35',
        color: '#FFF',
        weight: 3,
        opacity: 1,
        fillOpacity: 0.8
    }).addTo(map).bindPopup('Your Location');

    // Simulate real-time location updates
    simulateLocationUpdates();
    
    // Update map with current delivery if one is selected
    if (currentDelivery) {
        updateMapForDelivery(currentDelivery);
    }
    } catch (error) {
        console.error('Error initializing map:', error);
        const mapElement = document.getElementById('map');
        if (mapElement) {
            mapElement.innerHTML = '<p style="padding: 20px; text-align: center; color: #666;">Error loading map. Please refresh the page.</p>';
        }
    }
}

// Geocode addresses to get coordinates
async function geocodeDeliveryAddresses(delivery) {
    try {
        // Get pickup address (seller location - use a default or seller address if available)
        const pickupAddress = delivery.seller_address || delivery.seller_name || 'Manila, Philippines';
        
        // Get delivery address (customer address)
        const deliveryAddress = formatAddress(delivery.customer_address) || 'Manila, Philippines';
        
        // Geocode both addresses in parallel
        const [pickupCoords, deliveryCoords] = await Promise.all([
            geocodeAddress(pickupAddress),
            geocodeAddress(deliveryAddress)
        ]);
        
        // Store coordinates in delivery object
        if (pickupCoords) {
            delivery.pickupCoords = pickupCoords;
            delivery.pickupLocation = pickupAddress;
        }
        
        if (deliveryCoords) {
            delivery.deliveryCoords = deliveryCoords;
            delivery.deliveryLocation = deliveryAddress;
        }
        
        // If geocoding failed, use default Manila coordinates
        if (!pickupCoords) {
            delivery.pickupCoords = [14.5543, 120.9795]; // Default Manila coordinates
            delivery.pickupLocation = pickupAddress;
        }
        
        if (!deliveryCoords) {
            delivery.deliveryCoords = [14.5543, 120.9795]; // Default Manila coordinates
            delivery.deliveryLocation = deliveryAddress;
        }
    } catch (error) {
        console.error('Error geocoding addresses:', error);
        // Use default coordinates if geocoding fails
        delivery.pickupCoords = [14.5543, 120.9795];
        delivery.deliveryCoords = [14.5543, 120.9795];
        delivery.pickupLocation = delivery.seller_name || 'Pickup Location';
        delivery.deliveryLocation = formatAddress(delivery.customer_address) || 'Delivery Location';
    }
}

// Geocode a single address using Nominatim (OpenStreetMap)
async function geocodeAddress(address) {
    try {
        // Add Philippines to address if not already present for better results
        const searchAddress = address.includes('Philippines') || address.includes('PH') 
            ? address 
            : `${address}, Philippines`;
        
        const encodedAddress = encodeURIComponent(searchAddress);
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodedAddress}&limit=1`;
        
        const response = await fetch(url, {
            headers: {
                'User-Agent': 'RiderDashboard/1.0' // Required by Nominatim
            }
        });
        
        if (!response.ok) {
            throw new Error(`Geocoding failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data && data.length > 0) {
            const lat = parseFloat(data[0].lat);
            const lon = parseFloat(data[0].lon);
            return [lat, lon];
        }
        
        return null;
    } catch (error) {
        console.warn(`Failed to geocode address "${address}":`, error);
        return null;
    }
}

function updateMapForDelivery(delivery) {
    if (!map || !delivery) return;

    try {
        // Check if delivery has required coordinates
        if (!delivery.pickupCoords || !delivery.deliveryCoords) {
            console.warn('Delivery missing coordinates, attempting to geocode...', delivery);
            // Try to geocode if coordinates are missing
            geocodeDeliveryAddresses(delivery).then(() => {
                // Retry updating map after geocoding
                updateMapForDelivery(delivery);
            });
            return;
        }

    // Remove existing markers
        if (pickupMarker) {
            try {
                map.removeLayer(pickupMarker);
            } catch (e) {
                console.warn('Error removing pickup marker:', e);
            }
        }
        if (deliveryMarker) {
            try {
                map.removeLayer(deliveryMarker);
            } catch (e) {
                console.warn('Error removing delivery marker:', e);
            }
        }
        if (routePath) {
            try {
                map.removeLayer(routePath);
            } catch (e) {
                console.warn('Error removing route path:', e);
            }
        }

    // Add pickup marker
    pickupMarker = L.marker(delivery.pickupCoords, {
        icon: L.icon({
            iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0Ij48cGF0aCBkPSJNMTIgMEMxNi40MTggMCAyMCA0LjU4NyAyMCAxMGMwIDEwLTggMTAtOCAxMHMtOCAwLTgtMTBjMC01LjQxMyAzLjU4Mi0xMCA4LTEweiIgZmlsbD0iIzI3QUU2MCIvPjwvc3ZnPg==',
            iconSize: [24, 24],
            iconAnchor: [12, 24]
        })
        }).addTo(map).bindPopup(`<strong>Pickup:</strong> ${delivery.pickupLocation || 'Unknown'}`);

    // Add delivery marker
    deliveryMarker = L.marker(delivery.deliveryCoords, {
        icon: L.icon({
            iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0Ij48cGF0aCBkPSJNMTIgMEMxNi40MTggMCAyMCA0LjU4NyAyMCAxMGMwIDEwLTggMTAtOCAxMHMtOCAwLTgtMTBjMC01LjQxMyAzLjU4Mi0xMCA4LTEweiIgZmlsbD0iIzMwMDZENiIvPjwvc3ZnPg==',
            iconSize: [24, 24],
            iconAnchor: [12, 24]
        })
        }).addTo(map).bindPopup(`<strong>Delivery:</strong> ${delivery.deliveryLocation || 'Unknown'}`);

    // Draw route line
    routePath = L.polyline([delivery.pickupCoords, delivery.deliveryCoords], {
        color: '#FF6B35',
        weight: 3,
        opacity: 0.7,
        dashArray: '5, 5'
    }).addTo(map);

    // Fit map to show all markers
        const markers = [pickupMarker, deliveryMarker];
        if (userMarker) markers.push(userMarker);
        
        const group = L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.1));
    } catch (error) {
        console.error('Error updating map for delivery:', error);
    }
}

function simulateLocationUpdates() {
    // Update user location every 5 seconds (simulate GPS)
    setInterval(() => {
        try {
            if (map && userMarker && currentDelivery && currentDelivery.status !== 'completed') {
            // Random slight variation in location (±0.005)
            const latVariation = (Math.random() - 0.5) * 0.001;
            const lngVariation = (Math.random() - 0.5) * 0.001;
            
            const newLat = 14.5543 + latVariation;
            const newLng = 120.9795 + lngVariation;

            userMarker.setLatLng([newLat, newLng]);
            updateMapForDelivery(currentDelivery);
            }
        } catch (error) {
            console.warn('Error in location update simulation:', error);
        }
    }, 5000);
}

// =====================================================================
// EARNINGS SECTION
// =====================================================================

function updateEarningsReport() {
    // Helper function to safely set text content
    function safeSetText(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    // Get date inputs with defaults
    const startDateInput = document.getElementById('earningsStartDate');
    const endDateInput = document.getElementById('earningsEndDate');
    
    // Set default dates if not set (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    if (startDateInput && !startDateInput.value) {
        startDateInput.value = thirtyDaysAgo.toISOString().split('T')[0];
    }
    if (endDateInput && !endDateInput.value) {
        endDateInput.value = today.toISOString().split('T')[0];
    }

    const startDate = startDateInput ? new Date(startDateInput.value + 'T00:00:00') : thirtyDaysAgo;
    const endDate = endDateInput ? new Date(endDateInput.value + 'T23:59:59') : today;

    // Filter completed/delivered orders within date range
    // Use delivered_at if available, otherwise use created_at
    const filtered = deliveries.filter(d => {
        const status = (d.status || '').toLowerCase();
        if (status !== 'completed' && status !== 'delivered') return false;
        
        // Use delivered_at if available, otherwise created_at
        const deliveryDateStr = d.delivered_at || d.created_at;
        if (!deliveryDateStr) return false;
        
        const deliveryDate = new Date(deliveryDateStr);
        // Set time to start/end of day for proper comparison
        deliveryDate.setHours(0, 0, 0, 0);
        const start = new Date(startDate);
        start.setHours(0, 0, 0, 0);
        const end = new Date(endDate);
        end.setHours(23, 59, 59, 999);
        
        return deliveryDate >= start && deliveryDate <= end;
    });

    const serviceFeeRate = window.riderServiceFeePercentage || 2.5;
    
    const productSalesTotal = filtered.reduce((sum, d) => {
        const subtotal = parseFloat(d.product_subtotal ?? d.product_sales ?? d.total ?? 0);
        return sum + subtotal;
    }, 0);

    const deliveryFeeTotal = filtered.reduce((sum, d) => {
        const earnings = parseFloat(d.rider_earnings ?? d.delivery_fee ?? 0);
        if (earnings > 0) return sum + earnings;
        const subtotal = parseFloat(d.product_subtotal ?? d.product_sales ?? d.total ?? 0);
        return sum + (subtotal * (serviceFeeRate / 100));
    }, 0);

    const grossTotal = productSalesTotal;
    const platformFee = deliveryFeeTotal;
    const netTotal = deliveryFeeTotal;
    const count = filtered.length;

    // Update earnings display elements
    safeSetText('grossEarnings', formatCurrency(grossTotal));
    safeSetText('platformFee', formatCurrency(platformFee));
    safeSetText('totalEarnings', formatCurrency(netTotal));
    safeSetText('pendingPayout', formatCurrency(netTotal * 0.9));
    safeSetText('earningDeliveries', count);
    
    // Update fee display labels
    updateRiderFeeDisplay();

    // Update table
    const tbody = document.getElementById('earningsTableBody');
    if (!tbody) return;
    
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="no-data">No earnings data for the selected period</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(d => {
        const subtotal = parseFloat(d.product_subtotal ?? d.product_sales ?? d.total ?? 0);
        const earnings = parseFloat(d.rider_earnings ?? d.delivery_fee ?? 0) || (subtotal * (serviceFeeRate / 100));
        const gross = subtotal;
        const fee = earnings;
        const net = earnings;
        
        // Use delivered_at if available, otherwise created_at
        const deliveryDateStr = d.delivered_at || d.created_at;
        const deliveryDate = deliveryDateStr ? new Date(deliveryDateStr) : null;
        const dateDisplay = deliveryDate ? deliveryDate.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        }) : 'N/A';
        
        const customerName = d.customer_name || 'Unknown';
        const status = (d.status || 'unknown').toLowerCase();
        const statusDisplay = formatStatus(status);
        
        // Calculate distance (placeholder - would need actual distance calculation)
        const distance = d.distance || 'N/A';
        
        return `
        <tr>
            <td>${dateDisplay}</td>
            <td><strong>#${d.id || 'N/A'}</strong></td>
            <td>${customerName}</td>
            <td>${distance}${typeof distance === 'number' ? ' km' : ''}</td>
            <td>${formatCurrency(gross)}</td>
            <td style="color: #ff9800;">${formatCurrency(fee)}</td>
            <td style="color: #4caf50; font-weight: 600;">${formatCurrency(net)}</td>
            <td><span class="delivery-status status-${getStatusClass(status)}">${statusDisplay}</span></td>
        </tr>
        `;
    }).join('');
}

// =====================================================================
// DELIVERY HISTORY
// =====================================================================

function loadDeliveryHistory() {
    const selectedDate = document.getElementById('historyDate')?.value;
    const selectedStatus = document.getElementById('historyStatus')?.value;

    // Filter deliveries
    let filtered = deliveries.filter(d => {
        const status = (d.status || '').toLowerCase();
        
        // Status filter - handle completed/delivered
        if (selectedStatus) {
            if (selectedStatus === 'completed') {
                // Show both completed and delivered as "completed"
                if (status !== 'completed' && status !== 'delivered') {
                    return false;
                }
            } else if (selectedStatus === 'delivered') {
                // Show only delivered
                if (status !== 'delivered') {
                    return false;
                }
            } else if (status !== selectedStatus) {
                // For other statuses, exact match
                return false;
            }
        }
        
        // Date filter - use delivered_at if available, otherwise created_at
        if (selectedDate) {
            const deliveryDateStr = d.delivered_at || d.created_at;
            if (!deliveryDateStr) return false;
            
            const deliveryDate = new Date(deliveryDateStr);
            const filterDate = new Date(selectedDate);
            
            // Compare dates (ignore time)
            deliveryDate.setHours(0, 0, 0, 0);
            filterDate.setHours(0, 0, 0, 0);
            
            if (deliveryDate.getTime() !== filterDate.getTime()) {
                return false;
            }
        }
        
        return true;
    });

    // Sort by date (most recent first)
    filtered.sort((a, b) => {
        const dateA = new Date(a.delivered_at || a.created_at || 0);
        const dateB = new Date(b.delivered_at || b.created_at || 0);
        return dateB - dateA;
    });

    const timeline = document.getElementById('historyTimeline');
    if (!timeline) return;
    
    if (filtered.length === 0) {
        timeline.innerHTML = '<p class="no-data">No delivery history found for the selected filters</p>';
        return;
    }

    timeline.innerHTML = filtered.map((d, index) => {
        // Get order date/time
        const deliveryDateStr = d.delivered_at || d.created_at;
        const deliveryDate = deliveryDateStr ? new Date(deliveryDateStr) : null;
        const orderTime = deliveryDate ? deliveryDate.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }) : 'N/A';
        
        // Get customer name
        const customerName = d.customer_name || 'Unknown Customer';
        
        // Get pickup location (seller name)
        const pickupLocation = d.seller_name || 'Seller';
        
        // Get delivery address
        const deliveryAddress = formatAddress(d.customer_address) || 'Address not provided';
        
        // Get distance (placeholder if not available)
        const distance = d.distance || 'N/A';
        const distanceDisplay = typeof distance === 'number' ? `${distance} km` : distance;
        
        // Get delivery fee/amount
        const deliveryFee = parseFloat(d.delivery_fee) || 0;
        const amountDisplay = formatCurrency(deliveryFee);
        
        // Get status
        const status = (d.status || 'unknown').toLowerCase();
        const statusDisplay = formatStatus(status);
        const statusClass = getStatusClass(status);
        
        return `
        <div class="timeline-item">
            <div class="timeline-marker">${index + 1}</div>
            <div class="timeline-content">
                <h4>Order #${d.id || 'N/A'} - ${customerName}</h4>
                <p><strong>Order Time:</strong> ${orderTime}</p>
                <p><strong>Route:</strong> ${pickupLocation} → ${deliveryAddress}</p>
                <p><strong>Distance:</strong> ${distanceDisplay} | <strong>Amount:</strong> ${amountDisplay}</p>
                <p><strong>Status:</strong> <span class="delivery-status status-${statusClass}">${statusDisplay}</span></p>
            </div>
        </div>
        `;
    }).join('');
}

// =====================================================================
// STATISTICS SECTION
// =====================================================================

function loadStatistics() {
    // Helper function to safely set text content
    function safeSetText(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    // Helper function to safely set style width
    function safeSetWidth(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.width = value;
        }
    }

    // Calculate metrics from actual delivery data
    // Separate available orders from assigned orders
    const availableOrders = deliveries.filter(d => d.type === 'available').length;
    const assignedOrders = deliveries.filter(d => d.type === 'assigned').length;
    const totalAssigned = assignedOrders;
    
    // Completed deliveries (both 'completed' and 'delivered' status)
    const completedDeliveries = deliveries.filter(d => {
        const status = (d.status || '').toLowerCase();
        return (d.type === 'assigned' && (status === 'completed' || status === 'delivered'));
    }).length;
    
    // Calculate Acceptance Rate: (Assigned Orders) / (Available + Assigned Orders)
    // This shows what percentage of available orders the rider accepted
    const totalAvailable = availableOrders + assignedOrders;
    const acceptanceRate = totalAvailable > 0 ? (assignedOrders / totalAvailable) * 100 : 0;
    
    // Calculate Completion Rate: (Completed Deliveries) / (Assigned Orders)
    // This shows what percentage of accepted orders were completed
    const completionRate = totalAssigned > 0 ? (completedDeliveries / totalAssigned) * 100 : 0;
    
    // Calculate On-Time Delivery Rate
    // For now, we'll estimate based on completed deliveries within expected timeframe
    // In a real system, this would compare actual delivery time vs expected delivery time
    const onTimeDeliveries = deliveries.filter(d => {
        const status = (d.status || '').toLowerCase();
        if (status !== 'completed' && status !== 'delivered') return false;
        if (!d.delivered_at && !d.created_at) return false;
        
        // Estimate: if delivered within 2 hours of creation, consider it on-time
        const created = new Date(d.created_at);
        const delivered = new Date(d.delivered_at || d.created_at);
        const hoursDiff = (delivered - created) / (1000 * 60 * 60);
        return hoursDiff <= 2; // 2 hours threshold
    }).length;
    const onTimeRate = completedDeliveries > 0 ? (onTimeDeliveries / completedDeliveries) * 100 : 0;
    
    // Get rating from riderData (loaded from dashboard API)
    // The dashboard API returns average_rating in the dashboard object
    // We'll use a global variable to store the latest dashboard data
    let dashboardRating = 0;
    try {
        // Try to get rating from riderData first
        if (riderData && riderData.rating) {
            dashboardRating = parseFloat(riderData.rating);
        } else {
            // Fallback: check if we have dashboard data stored
            const dashboardData = window.lastDashboardData;
            if (dashboardData && dashboardData.average_rating) {
                dashboardRating = parseFloat(dashboardData.average_rating);
            }
        }
    } catch (e) {
        console.warn('Could not get rating:', e);
    }
    const rating = dashboardRating || 0;
    const satisfactionRate = rating * 20; // Convert 0-5 scale to 0-100%

    // Update progress bars
    safeSetWidth('acceptanceRateBar', Math.round(acceptanceRate) + '%');
    safeSetText('acceptanceRateText', Math.round(acceptanceRate) + '%');

    safeSetWidth('completionRateBar', Math.round(completionRate) + '%');
    safeSetText('completionRateText', Math.round(completionRate) + '%');

    safeSetWidth('onTimeRateBar', onTimeRate + '%');
    safeSetText('onTimeRateText', onTimeRate + '%');

    safeSetWidth('satisfactionRateBar', Math.round(satisfactionRate) + '%');
    safeSetText('satisfactionRateText', Math.round(satisfactionRate) + '%');

    // Update average rating if element exists
    safeSetText('avgRating', rating.toFixed(1));

    // Draw chart
    drawPerformanceChart();
}

function drawPerformanceChart() {
    const ctx = document.getElementById('performanceChart');
    if (!ctx) return;

    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js library not loaded. Chart will not be displayed.');
        ctx.parentElement.innerHTML = '<p style="padding: 20px; text-align: center; color: #666;">Chart library not loaded. Please refresh the page.</p>';
        return;
    }

    // Destroy existing chart if it exists
    if (ctx.chart) {
        ctx.chart.destroy();
    }

    try {
    // Calculate weekly data from actual deliveries
    const today = new Date();
    const dayOfWeek = today.getDay(); // 0 = Sunday, 1 = Monday, etc.
    
    // Get start of week (Monday)
    const startOfWeek = new Date(today);
    const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
    startOfWeek.setDate(today.getDate() - daysToMonday);
    startOfWeek.setHours(0, 0, 0, 0);
    
    // Calculate deliveries and earnings for each day of the week
    const weekDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const weeklyDeliveries = [0, 0, 0, 0, 0, 0, 0];
    const weeklyEarnings = [0, 0, 0, 0, 0, 0, 0];
    
    deliveries.forEach(d => {
        const status = (d.status || '').toLowerCase();
        // Only count completed/delivered orders
        if (status !== 'completed' && status !== 'delivered') return;
        
        // Use delivered_at if available, otherwise created_at
        const deliveryDateStr = d.delivered_at || d.created_at;
        if (!deliveryDateStr) return;
        
        const deliveryDate = new Date(deliveryDateStr);
        deliveryDate.setHours(0, 0, 0, 0);
        
        // Check if delivery is within this week
        if (deliveryDate >= startOfWeek) {
            const daysDiff = Math.floor((deliveryDate - startOfWeek) / (1000 * 60 * 60 * 24));
            if (daysDiff >= 0 && daysDiff < 7) {
                // Adjust for week start (Monday = 0, but array index needs adjustment)
                // If startOfWeek is Monday, daysDiff 0 = Monday, 1 = Tuesday, etc.
                const dayIndex = daysDiff;
                if (dayIndex >= 0 && dayIndex < 7) {
                    weeklyDeliveries[dayIndex]++;
                    const fee = parseFloat(d.delivery_fee) || 0;
                    weeklyEarnings[dayIndex] += fee;
                }
            }
        }
    });
    
    // Normalize earnings to show in hundreds for better chart scaling
    const earningsScaled = weeklyEarnings.map(e => Math.round(e / 100 * 10) / 10); // Scale to hundreds
    
    const data = {
        labels: weekDays,
        datasets: [
            {
                label: 'Deliveries',
                data: weeklyDeliveries,
                borderColor: '#FF6B35',
                backgroundColor: 'rgba(255, 107, 53, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                yAxisID: 'y'
            },
            {
                label: 'Earnings (₱100)',
                data: earningsScaled,
                borderColor: '#004E89',
                backgroundColor: 'rgba(0, 78, 137, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                yAxisID: 'y1'
            }
        ]
    };

        ctx.chart = new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    position: 'left',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Deliveries'
                    }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Earnings (₱100)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });
    } catch (error) {
        console.error('Error drawing performance chart:', error);
        ctx.parentElement.innerHTML = '<p style="padding: 20px; text-align: center; color: #666;">Error loading chart. Please refresh the page.</p>';
    }
}

// =====================================================================
// UTILITY FUNCTIONS
// =====================================================================

function setupEventListeners() {
    // Sidebar toggle
    const toggleBtn = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.rider-sidebar');
    
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });
    }

    // Status toggle
    const statusText = document.getElementById('statusText');
    const statusIndicator = document.getElementById('statusIndicator');
    
    if (statusText && statusIndicator) {
        // Initialize status if not set
        let currentStatus = statusText.textContent.toLowerCase().trim() || 'online';
        
        statusText.addEventListener('click', () => {
            currentStatus = currentStatus === 'online' ? 'offline' : 'online';
            statusText.textContent = capitalize(currentStatus);
            statusIndicator.classList.toggle('online');
            statusIndicator.classList.toggle('offline');
            showNotification(`Status changed to ${currentStatus}`, 'success');
        });
    }

    // Date filters
    document.getElementById('historyDate')?.addEventListener('change', loadDeliveryHistory);
    document.getElementById('historyStatus')?.addEventListener('change', loadDeliveryHistory);
    document.getElementById('earningsStartDate')?.addEventListener('change', updateEarningsReport);
    document.getElementById('earningsEndDate')?.addEventListener('change', updateEarningsReport);

    // Search functionality
    document.getElementById('searchInput')?.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const cards = document.querySelectorAll('.delivery-card');
        
        cards.forEach(card => {
            const text = card.textContent.toLowerCase();
            card.style.display = text.includes(query) ? 'grid' : 'none';
        });
    });
}

// =====================================================================
// RETURN PICKUPS SECTION
// =====================================================================

let allReturnPickups = [];
let currentReturnPickupFilter = 'all';

async function loadReturnPickups() {
    const container = document.getElementById('returnPickupsContainer');
    if (!container) return;

    try {
        const response = await authFetch('/api/riders/return-pickups');
        if (!response.ok) throw new Error('Failed to load return pickups');

        const data = await response.json();
        allReturnPickups = data.data?.pickups || data.pickups || [];

        // Update badge with available count
        const availableCount = allReturnPickups.filter(p => !p.pickup_rider_id).length;
        const badge = document.getElementById('returnPickupsBadge');
        if (badge) {
            if (availableCount > 0) {
                badge.textContent = availableCount;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }

        // Check for new pickups and show notification
        checkNewReturnPickups();

        renderReturnPickups(allReturnPickups);
    } catch (error) {
        console.error('Error loading return pickups:', error);
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #ef4444;">
                <i class="fas fa-exclamation-circle" style="font-size: 48px; margin-bottom: 16px;"></i>
                <p>Failed to load return pickups. Please try again later.</p>
            </div>
        `;
    }
}

function filterReturnPickups(filter, event) {
    currentReturnPickupFilter = filter;
    
    // Update filter buttons
    if (event) {
        const buttons = event.target.closest('.filter-buttons').querySelectorAll('.filter-btn');
        buttons.forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
    }
    
    let filtered = allReturnPickups;
    if (filter === 'available') {
        filtered = allReturnPickups.filter(p => !p.pickup_rider_id);
    } else if (filter === 'assigned') {
        filtered = allReturnPickups.filter(p => p.pickup_rider_id && !p.pickup_completed_at);
    } else if (filter === 'picked-up') {
        filtered = allReturnPickups.filter(p => p.pickup_completed_at && !p.item_received_at);
    }
    
    renderReturnPickups(filtered);
}

function getReturnPickupStatus(pickup) {
    if (!pickup.pickup_rider_id) {
        return { text: 'Available', color: '#ffc107', class: 'available' };
    } else if (pickup.pickup_rider_id && !pickup.pickup_scheduled_at) {
        return { text: 'Accepted', color: '#17a2b8', class: 'accepted' };
    } else if (pickup.pickup_scheduled_at && !pickup.pickup_completed_at) {
        return { text: 'On the Way', color: '#007bff', class: 'on-the-way' };
    } else if (pickup.pickup_completed_at && !pickup.item_received_at) {
        return { text: 'Picked Up', color: '#28a745', class: 'picked-up' };
    } else if (pickup.item_received_at) {
        return { text: 'Completed', color: '#6c757d', class: 'completed' };
    }
    return { text: 'Pending', color: '#6c757d', class: 'pending' };
}

function renderReturnPickups(pickups) {
    const container = document.getElementById('returnPickupsContainer');
    if (!container) return;

    if (pickups.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <i class="fas fa-inbox" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                <p style="color: #666;">No return pickup tasks found.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = pickups.map(pickup => {
        const status = getReturnPickupStatus(pickup);
        const isAssigned = pickup.pickup_rider_id !== null;
        const isPickedUp = pickup.pickup_completed_at !== null;
        const isCompleted = pickup.item_received_at !== null;
        const isAvailable = !isAssigned;
        
        const customerName = pickup.customer_name || (pickup.customer_first_name && pickup.customer_last_name ? `${pickup.customer_first_name} ${pickup.customer_last_name}` : 'Customer');
        const customerAddress = formatAddress(pickup.customer_address) || 'N/A';
        const sellerName = pickup.seller_name || 'Seller';
        const sellerAddress = pickup.seller_address || 'N/A';
        const productName = pickup.product_name || 'Product';
        
        return `
        <div class="delivery-card return-pickup-card-layout ${status.class} ${isAvailable ? 'available-order' : ''}">
            <div class="return-pickup-card-content">
                <div class="delivery-header return-pickup-header-full">
                    <h4>Return Pickup #${pickup.id} ${isAvailable ? '<span class="badge-available">Available</span>' : ''}</h4>
                    <span class="delivery-status status-${status.class}">${status.text}</span>
                </div>
                <div class="delivery-info">
                    <p><strong>Product:</strong> ${productName}</p>
                    <p><strong>Order #${pickup.order_id}</strong></p>
                    ${pickup.seller_name ? `
                        <p><i class="fas fa-store" style="color: #059669;"></i> ${sellerName}</p>
                    ` : ''}
                </div>
                <div class="delivery-info">
                    <p><strong>Customer:</strong> ${customerName}</p>
                    <p><strong>From:</strong> ${customerAddress}</p>
                </div>
                <div class="delivery-info">
                    <p><strong>Return To:</strong> ${sellerName}</p>
                    <p><strong>Address:</strong> ${sellerAddress}</p>
                </div>
                ${isAvailable ? `
                <div class="return-pickup-actions-right">
                    <button class="btn btn-secondary btn-sm" onclick="viewReturnPickupDetails(${pickup.id})">
                        <i class="fas fa-info-circle"></i> View Details
                    </button>
                    <button class="btn btn-primary btn-sm" onclick="acceptReturnPickup(${pickup.id})">
                        <i class="fas fa-check"></i> Accept Pickup
                    </button>
                </div>
                ` : `
                <div class="return-pickup-actions-right">
                    <button class="btn btn-secondary btn-sm" onclick="viewReturnPickupDetails(${pickup.id})">
                        <i class="fas fa-info-circle"></i> View Details
                    </button>
                </div>
                `}
            </div>
        </div>
        `;
    }).join('');
}

function checkNewReturnPickups() {
    // Check for new available pickups and show notification
    const availableCount = allReturnPickups.filter(p => !p.pickup_rider_id).length;
    if (availableCount > 0) {
        // Show notification if there are new pickups
        const lastCount = parseInt(localStorage.getItem('lastReturnPickupCount') || '0');
        if (availableCount > lastCount) {
            showNotification(`You have ${availableCount} new return pickup${availableCount > 1 ? 's' : ''} available!`, 'info');
        }
        localStorage.setItem('lastReturnPickupCount', availableCount.toString());
    }
}

async function acceptReturnPickup(requestId) {
    if (!confirm('Accept this return pickup task?')) return;

    try {
        const response = await authFetch(`/api/riders/return-pickups/${requestId}/accept`, {
            method: 'POST'
        });

        const data = await response.json();
        if (response.ok && data.success) {
            showNotification('Return pickup accepted successfully!', 'success');
            loadReturnPickups();
        } else {
            showNotification(data.error || 'Failed to accept pickup', 'error');
        }
    } catch (error) {
        console.error('Error accepting return pickup:', error);
        showNotification('Failed to accept pickup. Please try again.', 'error');
    }
}

async function markReturnPickupOnWay(requestId) {
    // This is a status update - we'll use the complete endpoint but could add a separate one
    showNotification('Status updated: On the way to customer', 'info');
    // Could add a separate API endpoint for status updates
}

async function markReturnPickupPickedUp(requestId) {
    if (!confirm('Mark this item as picked up from the customer? Make sure you have collected the item.')) return;

    try {
        const response = await authFetch(`/api/riders/return-pickups/${requestId}/complete`, {
            method: 'POST'
        });

        const data = await response.json();
        if (response.ok && data.success) {
            showNotification('Item marked as picked up! Now return it to the seller.', 'success');
            loadReturnPickups();
        } else {
            showNotification(data.error || 'Failed to update pickup status', 'error');
        }
    } catch (error) {
        console.error('Error updating pickup status:', error);
        showNotification('Failed to update pickup status. Please try again.', 'error');
    }
}

async function markReturnPickupDelivered(requestId) {
    if (!confirm('Mark this item as returned to the seller? Make sure you have delivered the item to the seller.')) return;

    try {
        const response = await authFetch(`/api/riders/return-pickups/${requestId}/mark-delivered`, {
            method: 'POST'
        });

        const data = await response.json();
        if (response.ok && data.success) {
            showNotification(data.message || 'Item marked as returned to seller!', 'success');
            loadReturnPickups();
        } else {
            showNotification(data.error || 'Failed to update delivery status', 'error');
        }
    } catch (error) {
        console.error('Error updating delivery status:', error);
        showNotification('Failed to update delivery status. Please try again.', 'error');
    }
}

async function viewReturnPickupDetails(requestId) {
    const pickup = allReturnPickups.find(p => p.id === requestId);
    if (!pickup) {
        showNotification('Pickup details not found', 'error');
        return;
    }

    showReturnPickupDetailsModal(pickup);
}

function showReturnPickupDetailsModal(pickup) {
    // Remove existing modal if any
    const existingModal = document.getElementById('returnPickupDetailsModal');
    if (existingModal) existingModal.remove();

    const status = getReturnPickupStatus(pickup);
    const isAssigned = pickup.pickup_rider_id !== null;
    const isPickedUp = pickup.pickup_completed_at !== null;
    const isCompleted = pickup.item_received_at !== null;

    const modalHTML = `
        <div id="returnPickupDetailsModal" class="modal" style="display: block;">
            <div class="modal-content modal-large return-pickup-details-modal">
                <div class="return-pickup-modal-header">
                    <div class="return-pickup-modal-header-left">
                        <button class="return-pickup-refresh-btn" onclick="loadReturnPickups(); showReturnPickupDetailsModal(pickup);" title="Refresh">
                            <i class="fas fa-sync-alt"></i>
                        </button>
                        <div class="return-pickup-modal-title-section">
                            <h2 class="return-pickup-modal-title">Return Pickup Details</h2>
                            <p class="return-pickup-modal-subtitle">Pickup ID: #${pickup.id} • Order #${pickup.order_id}</p>
                        </div>
                    </div>
                    <button class="return-pickup-modal-close" aria-label="Close" onclick="closeReturnPickupDetailsModal()">&times;</button>
                </div>
                <div class="return-pickup-modal-body">
                    <!-- Status Card -->
                    <div class="return-pickup-details-section">
                        <div class="return-pickup-section-header">
                            <i class="fas fa-info-circle"></i>
                            <h4>Pickup Status</h4>
                        </div>
                        <div class="return-pickup-status-display" style="background: ${status.color === '#ffc107' ? '#fef3c7' : status.color + '15'}; border-left: 4px solid ${status.color};">
                            <div class="return-pickup-status-label">CURRENT STATUS</div>
                            <div class="return-pickup-status-value" style="color: ${status.color};">
                                ${status.text}
                            </div>
                        </div>
                    </div>

                    <!-- Product Information -->
                    <div class="return-pickup-details-section">
                        <div class="return-pickup-section-header">
                            <i class="fas fa-box"></i>
                            <h4>Product Information</h4>
                        </div>
                        <div class="return-pickup-product-info">
                            ${pickup.product_image ? `
                                <div class="return-pickup-product-image-wrapper">
                                    <img src="${pickup.product_image.startsWith('http') ? pickup.product_image : 'http://127.0.0.1:5000' + pickup.product_image}" 
                                         alt="${pickup.product_name || 'Product'}"
                                         onerror="this.src='https://via.placeholder.com/120'">
                                </div>
                            ` : ''}
                            <div class="return-pickup-product-details">
                                <div class="return-pickup-product-name">${pickup.product_name || 'Product Name'}</div>
                                <div class="return-pickup-product-meta">
                                    <span class="return-pickup-order-number">Order #${pickup.order_id}</span>
                                </div>
                                ${pickup.seller_name ? `
                                    <div class="return-pickup-seller-info">
                                        <i class="fas fa-store"></i>
                                        <span>${pickup.seller_name}</span>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>

                    <!-- Customer Information -->
                    <div class="return-pickup-details-section">
                        <div class="return-pickup-section-header">
                            <i class="fas fa-user"></i>
                            <h4>Customer Information</h4>
                        </div>
                        <div class="return-pickup-customer-name">
                            ${pickup.customer_name || (pickup.customer_first_name && pickup.customer_last_name ? `${pickup.customer_first_name} ${pickup.customer_last_name}` : 'Customer')}
                        </div>
                        <div class="return-pickup-contact-list">
                            ${pickup.customer_phone ? `
                                <div class="return-pickup-contact-item">
                                    <i class="fas fa-phone return-pickup-contact-icon"></i>
                                    <span class="return-pickup-contact-value">${pickup.customer_phone}</span>
                                    <button class="return-pickup-action-btn return-pickup-call-btn" onclick="window.location.href='tel:${pickup.customer_phone}'">
                                        <i class="fas fa-phone"></i> Call
                                    </button>
                                </div>
                            ` : ''}
                            ${pickup.customer_email ? `
                                <div class="return-pickup-contact-item">
                                    <i class="fas fa-envelope return-pickup-contact-icon"></i>
                                    <span class="return-pickup-contact-value">${pickup.customer_email}</span>
                                </div>
                            ` : ''}
                            ${pickup.customer_address ? `
                                <div class="return-pickup-contact-item">
                                    <i class="fas fa-map-marker-alt return-pickup-contact-icon"></i>
                                    <span class="return-pickup-contact-value">${formatAddress(pickup.customer_address)}</span>
                                    <button class="return-pickup-action-btn return-pickup-navigate-btn" onclick="openMapForAddress('${formatAddress(pickup.customer_address)}')">
                                        <i class="fas fa-map"></i> Navigate
                                    </button>
                                </div>
                            ` : ''}
                        </div>
                    </div>

                    ${pickup.seller_address ? `
                        <!-- Seller Information -->
                        <div class="return-pickup-details-section">
                            <div class="return-pickup-section-header">
                                <i class="fas fa-store"></i>
                                <h4>Return To Seller</h4>
                            </div>
                            <div class="return-pickup-seller-name">
                                ${pickup.seller_name || 'Seller'}
                            </div>
                            <div class="return-pickup-contact-item">
                                <i class="fas fa-map-marker-alt return-pickup-contact-icon"></i>
                                <span class="return-pickup-contact-value">${pickup.seller_address}</span>
                                <button class="return-pickup-action-btn return-pickup-navigate-btn" onclick="openMapForAddress('${pickup.seller_address}')">
                                    <i class="fas fa-map"></i> Navigate
                                </button>
                            </div>
                        </div>
                    ` : ''}

                    <!-- Reason -->
                    <div class="return-pickup-details-section return-pickup-reason-section">
                        <div class="return-pickup-section-header">
                            <i class="fas fa-comment-dots"></i>
                            <h4>Return Reason</h4>
                        </div>
                        <div class="return-pickup-reason-text">${pickup.reason || 'No reason provided'}</div>
                    </div>

                    <!-- Evidence Images -->
                    ${pickup.evidence_images && pickup.evidence_images.length > 0 ? `
                        <div class="form-section-card">
                            <div class="form-section-header">
                                <i class="fa fa-images"></i>
                                <h4>Evidence Images</h4>
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px;">
                                ${pickup.evidence_images.map(img => `
                                    <div style="position: relative; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.3s;" 
                                         onmouseover="this.style.transform='scale(1.05)'" 
                                         onmouseout="this.style.transform='scale(1)'"
                                         onclick="window.open('${img.startsWith('http') ? img : 'http://127.0.0.1:5000' + img}', '_blank')">
                                        <img src="${img.startsWith('http') ? img : 'http://127.0.0.1:5000' + img}" 
                                             style="width: 100%; height: 120px; object-fit: cover; display: block;"
                                             onerror="this.src='https://via.placeholder.com/120'">
                                        <div style="position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.6); color: white; border-radius: 6px; padding: 4px 8px; font-size: 11px;">
                                            <i class="fa-solid fa-expand"></i>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Timeline -->
                    <div class="form-section-card">
                        <div class="form-section-header">
                            <i class="fa fa-clock-rotate-left"></i>
                            <h4>Pickup Timeline</h4>
                        </div>
                        <div style="position: relative; padding-left: 30px;">
                            <div style="position: absolute; left: 8px; top: 0; bottom: 0; width: 2px; background: linear-gradient(180deg, #28a745 0%, #17a2b8 50%, #ffc107 100%);"></div>
                            
                            <div style="position: relative; margin-bottom: 20px;">
                                <div style="position: absolute; left: -22px; width: 16px; height: 16px; border-radius: 50%; background: #28a745; border: 3px solid white; box-shadow: 0 0 0 2px #28a745;"></div>
                                <div style="background: #f8f9fa; border-radius: 10px; padding: 14px 16px; border: 1px solid #e9ecef;">
                                    <div style="font-weight: 600; color: var(--text-color); margin-bottom: 4px;">Request Created</div>
                                    <div style="color: var(--text-light); font-size: 13px;">${new Date(pickup.created_at).toLocaleString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                                </div>
                            </div>

                            ${pickup.pickup_scheduled_at ? `
                                <div style="position: relative; margin-bottom: 20px;">
                                    <div style="position: absolute; left: -22px; width: 16px; height: 16px; border-radius: 50%; background: #17a2b8; border: 3px solid white; box-shadow: 0 0 0 2px #17a2b8;"></div>
                                    <div style="background: #f8f9fa; border-radius: 10px; padding: 14px 16px; border: 1px solid #e9ecef;">
                                        <div style="font-weight: 600; color: var(--text-color); margin-bottom: 4px;">Pickup Accepted</div>
                                        <div style="color: var(--text-light); font-size: 13px;">${new Date(pickup.pickup_scheduled_at).toLocaleString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                                    </div>
                                </div>
                            ` : ''}
                            
                            ${pickup.pickup_completed_at ? `
                                <div style="position: relative; margin-bottom: 20px;">
                                    <div style="position: absolute; left: -22px; width: 16px; height: 16px; border-radius: 50%; background: #28a745; border: 3px solid white; box-shadow: 0 0 0 2px #28a745;"></div>
                                    <div style="background: #f8f9fa; border-radius: 10px; padding: 14px 16px; border: 1px solid #e9ecef;">
                                        <div style="font-weight: 600; color: var(--text-color); margin-bottom: 4px;">Item Picked Up</div>
                                        <div style="color: var(--text-light); font-size: 13px;">${new Date(pickup.pickup_completed_at).toLocaleString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                                    </div>
                                </div>
                            ` : ''}
                            
                            ${pickup.item_received_at ? `
                                <div style="position: relative; margin-bottom: 20px;">
                                    <div style="position: absolute; left: -22px; width: 16px; height: 16px; border-radius: 50%; background: #28a745; border: 3px solid white; box-shadow: 0 0 0 2px #28a745;"></div>
                                    <div style="background: #f8f9fa; border-radius: 10px; padding: 14px 16px; border: 1px solid #e9ecef;">
                                        <div style="font-weight: 600; color: var(--text-color); margin-bottom: 4px;">Returned to Seller</div>
                                        <div style="color: var(--text-light); font-size: 13px;">${new Date(pickup.item_received_at).toLocaleString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
                ${!isCompleted ? `
                    <div class="modal-actions-modern">
                        <button class="btn btn-cancel-modern" onclick="closeReturnPickupDetailsModal()">
                            <i class="fa fa-times"></i> Close
                        </button>
                        ${!isAssigned ? `
                            <button class="btn btn-save-modern" style="background: #10b981;" onclick="acceptReturnPickup(${pickup.id}); closeReturnPickupDetailsModal();">
                                <i class="fa fa-check"></i> Accept Pickup
                            </button>
                        ` : !isPickedUp ? `
                            <button class="btn" style="background: #3b82f6; color: white; padding: 10px 22px; border: none; border-radius: 8px; font-size: 14px; font-weight: 700; cursor: pointer; transition: transform 0.15s, box-shadow 0.15s; box-shadow: 0 6px 12px rgba(59, 130, 246, 0.3);" onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 8px 16px rgba(59, 130, 246, 0.35)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 6px 12px rgba(59, 130, 246, 0.3)'" onclick="markReturnPickupPickedUp(${pickup.id}); closeReturnPickupDetailsModal();">
                                <i class="fa fa-check-circle"></i> Mark Picked Up
                            </button>
                        ` : `
                            <button class="btn btn-save-modern" style="background: #10b981;" onclick="markReturnPickupDelivered(${pickup.id}); closeReturnPickupDetailsModal();">
                                <i class="fa fa-box-open"></i> Mark Returned to Seller
                            </button>
                        `}
                    </div>
                ` : `
                    <div class="modal-actions-modern">
                        <button class="btn btn-cancel-modern" onclick="closeReturnPickupDetailsModal()">
                            <i class="fa fa-times"></i> Close
                        </button>
                    </div>
                `}
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeReturnPickupDetailsModal() {
    const modal = document.getElementById('returnPickupDetailsModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function openMapForAddress(address) {
    const encodedAddress = encodeURIComponent(address);
    window.open(`https://www.google.com/maps/search/?api=1&query=${encodedAddress}`, '_blank');
}

// Expose functions globally
window.filterReturnPickups = filterReturnPickups;
window.viewReturnPickupDetails = viewReturnPickupDetails;
window.markReturnPickupOnWay = markReturnPickupOnWay;
window.markReturnPickupPickedUp = markReturnPickupPickedUp;
window.markReturnPickupDelivered = markReturnPickupDelivered;
window.closeReturnPickupDetailsModal = closeReturnPickupDetailsModal;

function formatCurrency(amount) {
    // Ensure amount is a number (convert from string if needed)
    const numAmount = parseFloat(amount) || 0;
    return '₱' + numAmount.toFixed(2);
}

function formatDate(date) {
    const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Date(date).toLocaleDateString('en-US', options);
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1).replace('-', ' ');
}

function showNotification(message, type = 'success') {
    // Use the same notification system as loginregister
    if (window.notify && typeof window.notify[type] === 'function') {
        window.notify[type](message);
    } else if (window.hubNotify && typeof window.hubNotify.show === 'function') {
        window.hubNotify.show(message, type);
    } else {
        // Fallback to simple alert if notification system not loaded
        console.warn('Notification system not loaded, using fallback');
        alert(message);
    }
}

function closeDeliveryModal() {
    const modal = document.getElementById('deliveryModal');
    modal.classList.remove('show');
}

// =====================================================================
// PROFILE SECTION
// =====================================================================

async function loadRiderProfile() {
    try {
        const response = await authFetch('/api/account/me');
        if (!response.ok) throw new Error('Failed to load profile');
        
        const data = await response.json();
        if (!data.success || !data.data) {
            console.warn('No profile data received');
            return;
        }
        
        const user = data.data;
        const rider = user.rider || {};
        
        // Helper function to safely set text content
        function safeSetText(elementId, value) {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = value || '-';
            }
        }
        
        // Helper function to safely set HTML content
        function safeSetHTML(elementId, value) {
            const element = document.getElementById(elementId);
            if (element) {
                element.innerHTML = value || '-';
            }
        }
        
        // Profile header
        const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim() || 'Rider';
        safeSetText('profileFullName', fullName);
        safeSetText('profileEmail', user.email || '-');
        
        // Profile picture/avatar
        const avatarUrl = user.avatar_url || (rider && rider.avatar_url);
        console.log('Profile picture URL:', avatarUrl, 'user.avatar_url:', user.avatar_url, 'rider.avatar_url:', rider && rider.avatar_url);
        const profileAvatarEl = document.getElementById('profileAvatar');
        const profileAvatarLargeEl = document.getElementById('profileAvatarLarge');
        
        if (avatarUrl) {
            console.log('Updating avatars with URL:', avatarUrl);
            // Update small avatar in sidebar
            if (profileAvatarEl) {
                profileAvatarEl.style.backgroundImage = `url(${avatarUrl})`;
                profileAvatarEl.style.backgroundSize = 'cover';
                profileAvatarEl.style.backgroundPosition = 'center';
                profileAvatarEl.textContent = '';
                console.log('Sidebar avatar updated');
            }
            // Update large avatar in profile section
            if (profileAvatarLargeEl) {
                profileAvatarLargeEl.style.backgroundImage = `url(${avatarUrl})`;
                profileAvatarLargeEl.style.backgroundSize = 'cover';
                profileAvatarLargeEl.style.backgroundPosition = 'center';
                profileAvatarLargeEl.textContent = '';
                console.log('Profile section avatar updated');
            }
        } else {
            console.log('No avatar URL found, using default');
            // Reset to default
            if (profileAvatarEl) {
                profileAvatarEl.style.backgroundImage = '';
                profileAvatarEl.textContent = '👤';
            }
            if (profileAvatarLargeEl) {
                profileAvatarLargeEl.style.backgroundImage = '';
                profileAvatarLargeEl.textContent = '👤';
            }
        }
        
        // Profile rating
        const rating = parseFloat(window.lastDashboardData?.average_rating) || 0;
        const ratingCount = 0; // TODO: Get actual rating count from API
        safeSetText('profileRatingCount', `(${ratingCount} ratings)`);
        
        // Update stars display
        const starsEl = document.getElementById('profileStars');
        if (starsEl) {
            const fullStars = Math.floor(rating);
            const hasHalfStar = rating % 1 >= 0.5;
            let starsHTML = '';
            for (let i = 0; i < 5; i++) {
                if (i < fullStars) {
                    starsHTML += '<i class="fas fa-star"></i>';
                } else if (i === fullStars && hasHalfStar) {
                    starsHTML += '<i class="fas fa-star-half-alt"></i>';
                } else {
                    starsHTML += '<i class="far fa-star"></i>';
                }
            }
            starsEl.innerHTML = starsHTML;
        }
        
        // Personal Information
        safeSetText('detailFullName', fullName);
        safeSetText('detailPhone', user.phone || rider.phone || '-');
        safeSetText('detailEmail', user.email || '-');
        safeSetText('detailVehicle', rider.vehicle_type ? capitalize(rider.vehicle_type) : '-');
        
        // Service Information
        const memberSince = user.created_at ? new Date(user.created_at).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        }) : '-';
        safeSetText('detailMemberSince', memberSince);
        
        const status = rider.status || 'active';
        const statusDisplay = status === 'active' ? 'Active' : 'Inactive';
        const statusClass = status === 'active' ? 'status-active' : 'status-inactive';
        safeSetHTML('detailStatus', `<span class="status-badge ${statusClass}">${statusDisplay}</span>`);
        
        // Total deliveries and earnings from dashboard data
        const totalDeliveries = deliveries.filter(d => {
            const s = (d.status || '').toLowerCase();
            return s === 'completed' || s === 'delivered';
        }).length;
        safeSetText('detailTotalDeliveries', totalDeliveries);
        
        const totalEarnings = deliveries
            .filter(d => {
                const s = (d.status || '').toLowerCase();
                return s === 'completed' || s === 'delivered';
            })
            .reduce((sum, d) => sum + (parseFloat(d.delivery_fee) || 0), 0);
        safeSetText('detailTotalEarnings', formatCurrency(totalEarnings));
        
    } catch (err) {
        console.error('Profile load error:', err);
        showNotification('Failed to load profile information', 'error');
    }
}

// Profile picture handling
let selectedProfilePicture = null;

function handleProfilePictureChange(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
        document.getElementById('editProfilePictureError').textContent = 'Invalid file type. Please select an image file (JPG, PNG, GIF, or WebP)';
        event.target.value = '';
        return;
    }
    
    // Validate file size (5MB max)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
        document.getElementById('editProfilePictureError').textContent = 'File too large. Maximum size is 5MB';
        event.target.value = '';
        return;
    }
    
    // Clear any previous errors
    document.getElementById('editProfilePictureError').textContent = '';
    
    // Store the file for upload
    selectedProfilePicture = file;
    
    // Show preview
    const reader = new FileReader();
    reader.onload = function(e) {
        const img = document.getElementById('profilePictureImg');
        const placeholder = document.querySelector('.profile-picture-placeholder');
        const removeBtn = document.getElementById('removeProfilePictureBtn');
        
        img.src = e.target.result;
        img.style.display = 'block';
        if (placeholder) placeholder.style.display = 'none';
        if (removeBtn) removeBtn.style.display = 'inline-block';
    };
    reader.readAsDataURL(file);
}

function removeProfilePicture() {
    selectedProfilePicture = null;
    const fileInput = document.getElementById('editProfilePicture');
    const img = document.getElementById('profilePictureImg');
    const placeholder = document.querySelector('.profile-picture-placeholder');
    const removeBtn = document.getElementById('removeProfilePictureBtn');
    
    if (fileInput) fileInput.value = '';
    if (img) {
        img.src = '';
        img.style.display = 'none';
    }
    if (placeholder) placeholder.style.display = 'flex';
    if (removeBtn) removeBtn.style.display = 'none';
    document.getElementById('editProfilePictureError').textContent = '';
}

async function editProfile() {
    // Load current profile data into form
    await loadRiderProfile();
    
    // Get current values
    const fullNameEl = document.getElementById('detailFullName');
    const phoneEl = document.getElementById('detailPhone');
    const emailEl = document.getElementById('detailEmail');
    const vehicleEl = document.getElementById('detailVehicle');
    
    if (fullNameEl) {
        const fullName = fullNameEl.textContent.trim();
        const nameParts = fullName.split(' ');
        document.getElementById('editFirstName').value = nameParts[0] || '';
        document.getElementById('editLastName').value = nameParts.slice(1).join(' ') || '';
    }
    if (phoneEl) {
        const phone = phoneEl.textContent.trim();
        document.getElementById('editPhone').value = phone !== '-' ? phone : '';
    }
    if (emailEl) {
        const email = emailEl.textContent.trim();
        document.getElementById('editEmail').value = email !== '-' ? email : '';
    }
    if (vehicleEl) {
        const vehicle = vehicleEl.textContent.trim().toLowerCase();
        document.getElementById('editVehicleType').value = vehicle !== '-' ? vehicle : '';
    }
    
    // Load current profile picture
    try {
        const response = await authFetch('/api/account/me');
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.data) {
                const user = data.data;
                const avatarUrl = user.avatar_url || (user.rider && user.rider.avatar_url);
                if (avatarUrl) {
                    const img = document.getElementById('profilePictureImg');
                    const placeholder = document.querySelector('.profile-picture-placeholder');
                    const removeBtn = document.getElementById('removeProfilePictureBtn');
                    
                    img.src = avatarUrl;
                    img.style.display = 'block';
                    if (placeholder) placeholder.style.display = 'none';
                    if (removeBtn) removeBtn.style.display = 'inline-block';
                }
            }
        }
    } catch (err) {
        console.warn('Could not load profile picture:', err);
    }
    
    // Reset selected picture
    selectedProfilePicture = null;
    
    // Show modal
    const modal = document.getElementById('editProfileModal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeEditProfileModal() {
    const modal = document.getElementById('editProfileModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
    // Clear form errors
    ['editFirstNameError', 'editLastNameError', 'editEmailError', 'editPhoneError', 'editVehicleTypeError', 'editProfilePictureError'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '';
    });
    // Reset profile picture selection
    selectedProfilePicture = null;
    const fileInput = document.getElementById('editProfilePicture');
    if (fileInput) fileInput.value = '';
}

async function saveProfile(event) {
    event.preventDefault();
    
    const saveBtn = document.getElementById('saveProfileBtn');
    if (saveBtn) {
        saveBtn.classList.add('loading');
    }
    
    // Clear previous errors
    ['editFirstNameError', 'editLastNameError', 'editEmailError', 'editPhoneError', 'editVehicleTypeError'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '';
    });
    
    const firstName = document.getElementById('editFirstName').value.trim();
    const lastName = document.getElementById('editLastName').value.trim();
    const email = document.getElementById('editEmail').value.trim();
    const phone = document.getElementById('editPhone').value.trim();
    const vehicleType = document.getElementById('editVehicleType').value.trim();
    
    // Validation
    let hasError = false;
    if (!firstName) {
        document.getElementById('editFirstNameError').textContent = 'First name is required';
        hasError = true;
    }
    if (!lastName) {
        document.getElementById('editLastNameError').textContent = 'Last name is required';
        hasError = true;
    }
    if (!email) {
        document.getElementById('editEmailError').textContent = 'Email is required';
        hasError = true;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        document.getElementById('editEmailError').textContent = 'Invalid email format';
        hasError = true;
    }
    
    if (hasError) {
        if (saveBtn) saveBtn.classList.remove('loading');
        return;
    }
    
    try {
        // Upload profile picture first if a new one is selected
        if (selectedProfilePicture) {
            try {
                const formData = new FormData();
                formData.append('picture', selectedProfilePicture);
                
                // For FormData, don't set Content-Type header - browser will set it with boundary
                // authFetch already handles this correctly
                const uploadResponse = await authFetch('/api/upload/profile-picture', {
                    method: 'POST',
                    body: formData
                });
                
                const uploadData = await uploadResponse.json();
                
                if (!uploadResponse.ok || !uploadData.success) {
                    const errorMsg = uploadData.error || 'Failed to upload profile picture';
                    document.getElementById('editProfilePictureError').textContent = errorMsg;
                    throw new Error(errorMsg);
                }
                
                console.log('Profile picture uploaded successfully:', uploadData);
                
                // Immediately update avatars with the new picture URL
                const newAvatarUrl = uploadData.data?.url || uploadData.data?.path;
                if (newAvatarUrl) {
                    console.log('Immediately updating avatars with new URL:', newAvatarUrl);
                    const profileAvatarEl = document.getElementById('profileAvatar');
                    const profileAvatarLargeEl = document.getElementById('profileAvatarLarge');
                    
                    if (profileAvatarEl) {
                        profileAvatarEl.style.backgroundImage = `url(${newAvatarUrl})`;
                        profileAvatarEl.style.backgroundSize = 'cover';
                        profileAvatarEl.style.backgroundPosition = 'center';
                        profileAvatarEl.textContent = '';
                    }
                    if (profileAvatarLargeEl) {
                        profileAvatarLargeEl.style.backgroundImage = `url(${newAvatarUrl})`;
                        profileAvatarLargeEl.style.backgroundSize = 'cover';
                        profileAvatarLargeEl.style.backgroundPosition = 'center';
                        profileAvatarLargeEl.textContent = '';
                    }
                }
            } catch (uploadErr) {
                console.error('Profile picture upload error:', uploadErr);
                // Don't fail the whole operation, but show the error
                document.getElementById('editProfilePictureError').textContent = uploadErr.message || 'Failed to upload picture';
                // Continue with other updates
            }
        }
        
        // Update all profile fields via /api/account/me endpoint
        // This endpoint handles both user fields (name, email, phone) and rider fields (vehicle_type)
        const updateData = {
            first_name: firstName,
            last_name: lastName,
            email: email
        };
        
        // Include phone if provided (even if empty, to allow clearing it)
        if (phone !== undefined && phone !== null) {
            updateData.phone = phone.trim();
        }
        
        // Include vehicle type if provided
        if (vehicleType) {
            updateData.vehicle_type = vehicleType;
        }
        
        console.log('Updating profile with data:', updateData);
        
        const response = await authFetch('/api/account/me', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            const errorMsg = data.error || 'Failed to update profile';
            console.error('Profile update failed:', errorMsg);
            throw new Error(errorMsg);
        }
        
        console.log('Profile updated successfully:', data);
        
        showNotification('Profile updated successfully!', 'success');
        closeEditProfileModal();
        
        // Wait a moment for the database to commit, then reload profile to show updated data
        setTimeout(async () => {
            // Reload dashboard first to update sidebar avatar
            await loadRiderDashboard();
            // Then reload profile to update profile section
            await loadRiderProfile();
            
            // Force reload profile section if it's currently active
            const profileSection = document.getElementById('profileSection');
            if (profileSection && profileSection.style.display !== 'none') {
                await loadRiderProfile();
            }
        }, 500);
        
    } catch (err) {
        console.error('Profile update error:', err);
        showNotification(err.message || 'Failed to update profile', 'error');
    } finally {
        if (saveBtn) saveBtn.classList.remove('loading');
    }
}

function changePassword() {
    // Clear form
    document.getElementById('changePasswordForm').reset();
    ['currentPasswordError', 'newPasswordError', 'confirmPasswordError'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '';
    });
    
    // Show modal
    const modal = document.getElementById('changePasswordModal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeChangePasswordModal() {
    const modal = document.getElementById('changePasswordModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
    // Clear form
    document.getElementById('changePasswordForm').reset();
    ['currentPasswordError', 'newPasswordError', 'confirmPasswordError'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '';
    });
}

async function savePassword(event) {
    event.preventDefault();
    
    const changeBtn = document.getElementById('changePasswordBtn');
    if (changeBtn) {
        changeBtn.classList.add('loading');
    }
    
    // Clear previous errors
    ['currentPasswordError', 'newPasswordError', 'confirmPasswordError'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '';
    });
    
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    // Validation
    let hasError = false;
    if (!currentPassword) {
        document.getElementById('currentPasswordError').textContent = 'Current password is required';
        hasError = true;
    }
    if (!newPassword) {
        document.getElementById('newPasswordError').textContent = 'New password is required';
        hasError = true;
    } else if (newPassword.length < 6) {
        document.getElementById('newPasswordError').textContent = 'Password must be at least 6 characters long';
        hasError = true;
    }
    if (!confirmPassword) {
        document.getElementById('confirmPasswordError').textContent = 'Please confirm your new password';
        hasError = true;
    } else if (newPassword !== confirmPassword) {
        document.getElementById('confirmPasswordError').textContent = 'Passwords do not match';
        hasError = true;
    }
    
    if (hasError) {
        if (changeBtn) changeBtn.classList.remove('loading');
        return;
    }
    
    try {
        const response = await authFetch('/api/auth/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to change password');
        }
        
        showNotification('Password changed successfully!', 'success');
        closeChangePasswordModal();
        
    } catch (err) {
        console.error('Password change error:', err);
        const errorMsg = err.message || 'Failed to change password';
        if (errorMsg.includes('Current password')) {
            document.getElementById('currentPasswordError').textContent = errorMsg;
        } else {
            showNotification(errorMsg, 'error');
        }
    } finally {
        if (changeBtn) changeBtn.classList.remove('loading');
    }
}

// Close modals when clicking outside (extend existing handler)
const originalOnClick = window.onclick;
window.onclick = function(event) {
    // Call original handler if it exists
    if (originalOnClick) {
        originalOnClick(event);
    }
    
    // Handle profile modals
    const editModal = document.getElementById('editProfileModal');
    const passwordModal = document.getElementById('changePasswordModal');
    if (event.target === editModal) {
        closeEditProfileModal();
    }
    if (event.target === passwordModal) {
        closeChangePasswordModal();
    }
}

function logout() {
        showNotification('Logging out...', 'success');
        localStorage.removeItem('hub_access_token');
        localStorage.removeItem('hub_refresh_token');
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1000);
}

// Scroll event for sidebar
document.addEventListener('scroll', () => {
    const sidebar = document.querySelector('.rider-sidebar');
    if (window.innerWidth <= 768 && sidebar.classList.contains('active')) {
        // Auto-close on scroll for mobile
    }
});

// Load Chart.js for statistics
if (document.querySelector('script[src*="chart.js"]')) {
    console.log('Chart.js loaded successfully');
}

console.log('Rider Dashboard initialized successfully!');
